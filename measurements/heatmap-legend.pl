#!/usr/bin/perl -w

use strict;
use warnings;
use POSIX;

use Data::Dump;

my $infile = $ARGV[0];
print "% Processing input file $infile\n";

open my $hInfile, '<', $infile or die "Error: failed to open input file $infile\n";

use constant {
  STATE_PREAMBLE => 0,
  STATE_BACKGROUND => 1,
  STATE_LEGEND => 2,
};

use constant {
  TYPE_FOREGROUND => 0,
  TYPE_BACKGROUND => 1,
  TYPE_TEXT => 2,
  TYPE_UNKNOWN => 3,
  TYPE_SKIP => 4,
};
my $state = STATE_PREAMBLE;

# regexes
my $rgxScopeBegin = qr/^\\begin\{scope\}/;
my $rgxScopeEnd = qr/^\\end\{scope\}/;

my $line;
my $linenr = 1;

my $is_background = 0;
my $data = {};
my $defined_type = TYPE_UNKNOWN;

my @backgrounds = ();
my @foregrounds = ();
my @texts = ();

while (<$hInfile>) {
  $line = $_;

  if ($state == STATE_PREAMBLE
      || $state == STATE_BACKGROUND) {
    if ($line =~ m/$rgxScopeBegin/) {
      $state++;
    }

    # print("% $state: [$linenr]\n");
    if ($state != STATE_LEGEND
        && $state != STATE_BACKGROUND) {
      print("$line");
    }
  }
  elsif ($state == STATE_LEGEND) {
    if ($line =~ m/$rgxScopeBegin/) {
      # print("% BEGIN DEFINITION\n");
      $is_background = 0;

      $data = {};
      $defined_type = TYPE_UNKNOWN;
    }
    elsif ($line =~ m/^\\path\[clip\]\s+\(\s*([0-9\.]+),\s*([0-9\.]+)\)\s+rectangle\s+\(\s*([0-9\.]+),\s*([0-9\.]+)\);/) {
      # print("% CLIP ($1, $2) rectangle ($3, $4)\n");
      my @d = ($1*1, $2*1, $3*1, $4*1);
      $data->{'clip'} = \@d;
    }
    elsif ($line =~ m/^\\definecolor\{([^\}]+)\}\{([^\}]+)\}\{([^\}]+)\}/) {
      # print("% COLOR $1 $2 $3\n");

      my $name = $1;
      my $type = $2;
      my $value = $3;
      if ($name eq 'fillColor') {
        if ($type eq 'gray') {
          $defined_type = TYPE_BACKGROUND;
        }
        else {
          $defined_type = TYPE_FOREGROUND;

          if ($value eq '255,255,255') {
            $defined_type = TYPE_SKIP;
          }
        }

        my @d = ($1, $2, $3);
        $data->{'fillcolor'} = \@d;
      }
    }
    elsif ($line =~ m/^\\path\[([^\]]+)\]\s+\(\s*([0-9\.]+),\s*([0-9\.]+)\)\s+rectangle\s+\(\s*([0-9\.]+),\s*([0-9\.]+)\);/) {
      # print("% RECTANGLE $1 $2 $3 $4 $5\n");

      my @d = ($1, $2*1, $3*1, $4*1, $5*1);
      $data->{'rect'} = \@d;
    }
    elsif ($line =~ m/^\\node\[(text[^\]]+)\] at \(\s*([0-9\.]+),\s*([0-9\.]+)\) \{([^\}]+)\}/) {
      # print("% TEXT $1 $2 $3 $4\n");
      $defined_type = TYPE_TEXT;

      my @d = ($1, $2*1, $3*1, $4);
      $data->{'text'} = \@d;
    }
    elsif ($line =~ m/$rgxScopeEnd/) {
      # print("% END DEFINITION at $linenr\n");
      $data->{'line'} = $linenr;

      if ($defined_type == TYPE_BACKGROUND) {
        # print("% --- adding to background\n");
        push @backgrounds, $data;
      }
      elsif ($defined_type == TYPE_FOREGROUND) {
        # print("% --- adding to foreground\n");
        push @foregrounds, $data;
      }
      elsif ($defined_type == TYPE_TEXT) {
        # print("% --- adding to text\n");
        push @texts, $data;
      }
      elsif ($defined_type == TYPE_SKIP) {
        # print("% --- skip\n");
      }
      else {
        die;
      }
    }
  }

  $linenr++
}

my $new_items_per_row = floor(($#foregrounds + 1)/2);

# 1. FILLED SQUARES
{
  my $delta_x = $foregrounds[1]{'rect'}[1] - $foregrounds[0]{'rect'}[1];

  my $row1_x = $foregrounds[0]{'rect'}[1];
  my $row1_y = $foregrounds[0]{'rect'}[2];
  my $row2_x = $foregrounds[$new_items_per_row/2]{'rect'}[1];
  my $row2_y = $foregrounds[$new_items_per_row/2]{'rect'}[2];

  for my $idx (0 .. $#foregrounds) {
    my $xbase = $row1_x;
    my $ybase = $row1_y;
    my $row_index = $idx;
    if ($idx >= $new_items_per_row) {
      $xbase = $row2_x;
      $ybase = $row2_y;
      $row_index = $idx - $new_items_per_row;
    }

    my $orig_x1 = $foregrounds[$idx]{'rect'}[1];
    my $orig_y1 = $foregrounds[$idx]{'rect'}[2];
    my $orig_x2 = $foregrounds[$idx]{'rect'}[3];
    my $orig_y2 = $foregrounds[$idx]{'rect'}[4];

    $foregrounds[$idx]{'rect'}[1] = $xbase + $row_index * $delta_x;
    $foregrounds[$idx]{'rect'}[2] = $ybase;
    $foregrounds[$idx]{'rect'}[3] = $xbase + $row_index * $delta_x + ($orig_x2 - $orig_x1);
    $foregrounds[$idx]{'rect'}[4] = $ybase + ($orig_y2 - $orig_y1);
    # dd $foregrounds[$idx];

    print("\\begin{scope}\n");

    my $a = $foregrounds[$idx]{'clip'}[0];
    my $b = $foregrounds[$idx]{'clip'}[1];
    my $c = $foregrounds[$idx]{'clip'}[2];
    my $d = $foregrounds[$idx]{'clip'}[3];
    print("  \\path[clip] (  $a,  $b) rectangle ($c,$d);\n");

    my $e = $foregrounds[$idx]{'fillcolor'}[0];
    my $f = $foregrounds[$idx]{'fillcolor'}[1];
    my $g = $foregrounds[$idx]{'fillcolor'}[2];
    print("  \\definecolor{$e}{$f}{$g}\n");

    my $h = $foregrounds[$idx]{'rect'}[0];
    my $i = $foregrounds[$idx]{'rect'}[1];
    my $j = $foregrounds[$idx]{'rect'}[2];
    my $k = $foregrounds[$idx]{'rect'}[3];
    my $l = $foregrounds[$idx]{'rect'}[4];
    print("  \\path[$h] ($i,$j) rectangle ($k,$l);\n");

    print("\\end{scope}\n");
  }
}

# 2. LABELS
{
  my $delta_x = $texts[1]{'text'}[1] - $texts[0]{'text'}[1];

  my $row1_x = $texts[0]{'text'}[1];
  my $row1_y = $texts[0]{'text'}[2];
  my $row2_x = $texts[$new_items_per_row/2]{'text'}[1];
  my $row2_y = $texts[$new_items_per_row/2]{'text'}[2];

  for my $idx (0 .. $#texts) {
    my $xbase = $row1_x;
    my $ybase = $row1_y;
    my $row_index = $idx;
    if ($idx >= $new_items_per_row) {
      $xbase = $row2_x;
      $ybase = $row2_y;
      $row_index = $idx - $new_items_per_row;
    }

    my $orig_x1 = $texts[$idx]{'text'}[1];
    my $orig_y1 = $texts[$idx]{'text'}[2];

    $texts[$idx]{'text'}[1] = $xbase + $row_index * $delta_x;
    $texts[$idx]{'text'}[2] = $ybase;
    # dd $texts[$idx];

    print("\\begin{scope}\n");

    my $a = $texts[$idx]{'clip'}[0];
    my $b = $texts[$idx]{'clip'}[1];
    my $c = $texts[$idx]{'clip'}[2];
    my $d = $texts[$idx]{'clip'}[3];
    print("  \\path[clip] (  $a,  $b) rectangle ($c,$d);\n");

    print("  \\definecolor{drawColor}{RGB}{0,0,0}\n");

    my $h = $texts[$idx]{'text'}[0];
    my $i = $texts[$idx]{'text'}[1];
    my $j = $texts[$idx]{'text'}[2];
    my $k = $texts[$idx]{'text'}[3];
    print("  \\node[$h] at ($i,$j) {$k};\n");

    print("\\end{scope}\n");
  }
}

print("\\end{tikzpicture}\n");
print("\\gdef\\rcaption{}\n");
