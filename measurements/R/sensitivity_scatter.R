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

for (i in seq(1, length(args), by=2)) {
  csvfile <- args[i]
  dataset <- args[i+1]

  subdf <- readcsv(csvfile)

  # collect scatter data
  names(subdf) <- c('category', 'X', 'Y', 'E')
  subdf$dataset <- sanitize_text(dataset)

  df <- rbind(df, subdf)
}
df$Y <- df$Y*100

x_axis_limits <- range(pretty(df$X))
x_axis_breaks <- sort(unique(df$X))

nr_false_edges <- df[which(df$category=='FPR (GUI)' & df$dataset=='No attack'), ][c("X", "E")]
nr_true_edges <- df[which(df$category=='FNR (GUI)' & df$dataset=='No attack'), ][c("X", "E")]

all_data <- df

# generate data to format the secondary Y-axis
primary_breaks <- c(0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)
edges_breaks <- primary_breaks
edges_labels <- edges_breaks
nr_edges_max <- 100
secondary_label <- ""

if (nrow(nr_false_edges) > 0) {
  # here we overwrite the 'all_data'

  # rescale the number of edges so we can generate the secondary Y-axis
  nr_edges_max = max(max(nr_false_edges$E), max(nr_true_edges$E))
  nr_false_edges$Y <- nr_false_edges$E/nr_edges_max*100
  nr_true_edges$Y <- nr_true_edges$E/nr_edges_max*100

  edges_breaks <- primary_breaks * nr_edges_max/100
  edges_labels <- round(edges_breaks/1000, 0)

  # create unified data frame of all the edge data
  nr_false_edges$category <- rep("Fake edges", nrow(nr_false_edges))
  nr_false_edges$dataset <- rep("Edge counts", nrow(nr_false_edges))
  nr_true_edges$category <- rep("True edges", nrow(nr_true_edges))
  nr_true_edges$dataset <- rep("Edge counts", nrow(nr_true_edges))
  all_edges <- rbind(nr_false_edges, nr_true_edges)

  # finally collect the other data
  all_data <- rbind(all_edges, df)

  secondary_label <- "Edge count (x1000)"
}

all_data$sizes <- 1
# larger diamonds
all_data$sizes[all_data$category == 'FPR (GUI)'] <- 1.5

# colors and shapes for the false rates and true/false edges
colors <- c("red4", "red1", "dodgerblue4", "dodgerblue1", "gray70", "gray70")
shapes <- c(19, 17, 15, 18, 10, 12)
sizes <- c(rep(1, nrow(all_data[all_data$category == 'FNR (DB)', ])), rep(1, nrow(all_data[all_data$category == 'FNR (GUI)', ])), rep(1, nrow(all_data[all_data$category == 'FPR (DB)', ])), rep(3, nrow(all_data[all_data$category == 'FPR (GUI)', ])), rep(1, nrow(all_data[all_data$category == 'True edges', ])), rep(1, nrow(all_data[all_data$category == 'Fake edges', ])))
# line types for the attack scenarios
linetypes <- c(1, 3, 4, 2)

# deterministic order of legend, i.e., as specified on the command-line
all_data$dataset <- factor(all_data$dataset, levels=unique(all_data$dataset), ordered = TRUE)

# plot multiple data sets on one chart
g <- ggplot(NULL)

g <- g +
  geom_point(data=all_data, aes(x=X, y=Y, color=category, shape=category), size=all_data$sizes) +
  geom_line(data=all_data, aes(x=X, y=Y, color=category, linetype=dataset), size=0.5) +
  theme(legend.box.margin=margin(-5,0,0,0), legend.box = "vertical", legend.spacing.x = unit(0, "cm"), legend.spacing.y = unit(0, "cm"), legend.title=element_text(size=10), legend.position=legendposition) +
  scale_x_continuous(expand=c(0, 0), breaks=x_axis_breaks, limits=x_axis_limits) +
  scale_y_continuous(expand=c(0, 0.05), breaks=primary_breaks, limits=range(0, 100), sec.axis = sec_axis(~.*nr_edges_max/100, breaks=edges_breaks, labels=edges_labels, name=secondary_label)) +
  scale_color_manual(name="Left axis          Right axis", values=colors, guide=guide_legend(nrow=4, order=1, title.vjust=1)) +
  scale_shape_manual(name="Left axis          Right axis", values=shapes, guide=guide_legend(nrow=4, order=1)) +
  scale_linetype_manual(name="", values=linetypes, guide=guide_legend(nrow=3, order=2)) +
  labs(x=sanitize_text(" "),
      y=sanitize_text("false rate %"))

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
