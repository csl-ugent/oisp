#!/usr/bin/env Rscript

# ./sensitivity_scatter.R no_atk.csv "No attack" atk_db.csv "Soundish attack" atk_gui.csv "Unsound attack"

source_local <- function(fname){
    argv <- commandArgs(trailingOnly = FALSE)
    base_dir <- dirname(substring(argv[grep("--file=", argv)], 8))
    source(paste(base_dir, fname, sep="/"))
}
source_local("helpers.R")
install_and_import(c("grid", "gridExtra"))

# don't draw a legend by default
legendposition <- 'none'

debug <- FALSE
if (debug) {
  legendposition <- 'right'
}

legend_only <- FALSE
if (legend_only) {
  legendposition <- 'right'
}

# 1. AGGREGATE THE CSV DATA
# INPUT = CSV file with, on each line:
# <benchmark>,<dispatcher>,<total>,<fraction>,<cat1>,<cat2>,...
args <- commandArgs(trailingOnly=TRUE)
if (length(args) == 0) {
  stop("first argument should be CSV file")
}

output_to_tex(paste(csvfile, '.tex', sep=''), width=3.5, height=2.5)

df <- data.frame(category=numeric(), X=numeric(), Y=numeric(), dataset=character())

for (i in seq(1, length(args), by=3)) {
  dataset <- args[i+2]

  # collect scatter data
  csvfile1 <- args[i]
  subdf1 <- readcsv(csvfile1)
  names(subdf1) <- c('category', 'X', 'Y', 'E')
  subdf1$dataset <- sanitize_text(paste(dataset, '1', sep=''))
  subdf1$series <- '1'
  df <- rbind(df, subdf1)

  csvfile2 <- args[i+1]
  subdf2 <- readcsv(csvfile2)
  names(subdf2) <- c('category', 'X', 'Y', 'E')
  subdf2$dataset <- sanitize_text(paste(dataset, '2', sep=''))
  subdf2$series <- '2'
  df <- rbind(df, subdf2)
}
df$Y <- df$Y*100

x_axis_limits <- range(pretty(df$X))
x_axis_breaks <- sort(unique(df$X))

all_data <- df

# generate data to format the secondary Y-axis
primary_breaks <- c(0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)

# colors and shapes for the false rates and true/false edges
colors <- c("red4", "red1", "dodgerblue4", "dodgerblue1", "gray70", "gray70")
shapes <- c(19, 19,     17,     15,            18,            10,       12)
# line types for the attack scenarios
linetypes <- c(3, 3, 4, 4, 2, 2)

# deterministic order of legend, i.e., as specified on the command-line
all_data$dataset <- factor(all_data$dataset, levels=unique(all_data$dataset), ordered = TRUE)

# marker sizes
all_data$sizes <- 1

# plot multiple data sets on one chart
g <- ggplot(NULL)

g <- g +
  geom_point(data=all_data, aes(x=X, y=Y, color=series, shape=category), size=all_data$sizes) +
  geom_line(data=all_data, aes(x=X, y=Y, color=series, linetype=dataset), size=0.5) +
  theme(legend.box.margin=margin(-5,0,0,0), legend.box = "vertical", legend.spacing.x = unit(0, "cm"), legend.spacing.y = unit(0, "cm"), legend.title=element_text(size=10), legend.position=legendposition) +
  scale_x_continuous(expand=c(0, 0), breaks=x_axis_breaks, limits=x_axis_limits) +
  scale_y_continuous(expand=c(0, 0.05), breaks=primary_breaks, limits=range(0, 100)) +
  scale_color_manual(name="Left axis          Right axis", values=colors, guide=guide_legend(nrow=4, order=1, title.vjust=1)) +
  scale_shape_manual(name="Left axis          Right axis", values=shapes, guide=guide_legend(nrow=4, order=1)) +
  scale_linetype_manual(name="", values=linetypes, guide=guide_legend(nrow=3, order=2)) +
  labs(x=sanitize_text(" "),
      y=sanitize_text("fraction of broken pairs %"))

# helper to extract legend from a plot
g_legend<-function(plt) {
  tmp <- ggplot_gtable(ggplot_build(plt))
  leg <- which(sapply(tmp$grobs, function(x) x$name) == "guide-box")
  legend <- tmp$grobs[[leg]]
  return(legend)
}

if (legend_only) {
  legend <- g_legend(g)
  grid.newpage()
  grid.draw(legend)
} else {
  g
}

output_finish()
