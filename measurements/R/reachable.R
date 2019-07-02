#!/usr/bin/env Rscript
source_local <- function(fname){
    argv <- commandArgs(trailingOnly = FALSE)
    base_dir <- dirname(substring(argv[grep("--file=", argv)], 8))
    source(paste(base_dir, fname, sep="/"))
}
source_local("helpers.R")

install_and_import("cowplot")
theme_set(theme_cowplot(font_size=10))

debug <- FALSE

# INPUT = CSV file with, on each line:
# <benchmark>,<dispatcher>,<total>,<fraction>,<cat1>,<cat2>,...
args <- commandArgs(trailingOnly=TRUE)
if (length(args) == 0) {
  stop("first argument should be CSV file")
}
csvfile <- args[1]

# read CSV file and replace NA (empty) values with 0
df <- readcsv(csvfile)
names(df) <- c("stage", "category", "x", "y", "fraction")

# extract final origin information
df$fraction <- round(df$fraction * 100, digits=1)
df <- df[df$fraction != 0, ]

cat(sprintf("%% Command: %s\n", paste(commandArgs(), collapse=" ")))
cat(sprintf("%% Source data: %s\n", csvfile))
cat(sprintf("%%\n"))

output_to_tex(paste(csvfile, '.tex', sep=''), width=6, height=3)

setup_data <- function(df, selector, lab, dodge) {
  # extract data to plot
  data <- df[grep(selector, df$category), ]

  # make sure that each subset holds the same X ticks
  subdata_init_ticks <- data[grep("initial", data$stage), ]$x
  subdata_fini_ticks <- data[grep("final", data$stage), ]$x

  all_ticks <- union(subdata_init_ticks, subdata_fini_ticks)

  for (i in setdiff(all_ticks, subdata_init_ticks)) {
    data[nrow(data) + 1,] = list("initial", selector, i, 0, 0)
  }

  for (i in setdiff(all_ticks, subdata_fini_ticks)) {
    data[nrow(data) + 1,] = list("final", selector, i, 0, 0)
  }

  data$x <- factor(data$x)
  data$stage <- factor(data$stage, levels=c("initial", "final"))

  return(ggplot(data, aes(x, fraction)) +
    geom_col(aes(fill = stage), width = 0.3, position = position_dodge(width=0.5), stat="identity") +
    labs(x=lab, y=sanitize_text("instructions (%)")) +
    theme(legend.position="none", legend.title = element_blank()) +
    scale_y_continuous(expand=expand_scale(c(0, 0.35)), limits=c(0, 100), breaks=c(0, 20, 40, 60, 80, 100)) +
    geom_text(aes(label=sprintf("%0.1f", round(fraction, digits=1)), group=stage), angle=90, size=3, hjust=-0.3, position=position_dodge(width=dodge)) +
    scale_fill_manual(values=c("red1", "dodgerblue1")))
}

# rel_widths is hardcoded and hence tailored to each specific set of plots
top_row <- plot_grid(setup_data(df, "reachable_by_library", "archives", 0.9), setup_data(df, "reachable_by_object", "object files", 0.9), ncol=2, align='h', rel_widths=c(8/19*1.7, 15/19*1.5))
plot_grid(top_row, setup_data(df, "reachable_by_function", "functions", 0.75), ncol=1)

output_finish()
