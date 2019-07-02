#!/usr/bin/env Rscript
source_local <- function(fname){
    argv <- commandArgs(trailingOnly = FALSE)
    base_dir <- dirname(substring(argv[grep("--file=", argv)], 8))
    source(paste(base_dir, fname, sep="/"))
}
source_local("helpers.R")
debug <- FALSE

install_and_import("ggrepel")

cat(sprintf("%% Command: %s\n", paste(commandArgs(), collapse=" ")))
cat(sprintf("%%\n"))

output_to_tex(paste(csvfile, '.tex', sep=''), width=5, height=5)

plots <- list()

g <- ggplot(NULL)
linetypes <- c("solid", "dashed")
counter <- 0

for (i in commandArgs(trailingOnly=TRUE)) {
  # read input file line by line and collect the data
  all_data <- data.frame(benchmark=character(), dispatcher=character(), value=numeric())

  collect <- function(line) {
    # modify global variable
    all_data <<- rbind(all_data, readRuntimeMeasurementFile(line), stringsAsFactors=FALSE)
  }
  for_each_line_in_file(i, collect)
  overhead_data <- convertRuntimeMeasurementsToRelative(all_data)
  overhead_data$value <- overhead_data$value - 100

  if (debug) {
    overhead_data
  }

  xlabformatter <- function(x) {
    lab <- sprintf('%.0fk', x/1000)
  }

  overhead_data$catnum <- as.numeric(overhead_data$cat)

  px <- pretty(overhead_data$catnum, n=14)

  linetype <- "solid"
  if (counter == 1) {
    linetype <- "dashed"
  }

  g <- g + geom_point(data=overhead_data, aes(x=catnum, y=value, shape=benchmark, color=benchmark)) +
    geom_line(linetype=linetype, data=overhead_data, aes(x=catnum, y=value, shape=benchmark, color=benchmark)) +
    theme(axis.text.x=element_text(angle=60, hjust=1), legend.position="bottom", legend.title=element_blank()) +
    geom_hline(yintercept=0, color = "black", linetype="dashed", size=0.25) +
    scale_x_continuous(breaks=px, limits=range(px), label=xlabformatter) +
    labs( x="Number of factored fragments",
          y=sanitize_text("Overhead (%)"))

  counter <- counter + 1
}

g

output_finish()
