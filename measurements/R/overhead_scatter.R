#!/usr/bin/env Rscript
source_local <- function(fname){
    argv <- commandArgs(trailingOnly = FALSE)
    base_dir <- dirname(substring(argv[grep("--file=", argv)], 8))
    source(paste(base_dir, fname, sep="/"))
}
source_local("helpers.R")
debug <- FALSE

install_and_import("ggrepel")
library("ggrepel")

# read input file line by line and collect the data
all_data <- data.frame(benchmark=character(), dispatcher=character(), value=numeric())

collect <- function(line) {
  # modify global variable
  all_data <<- rbind(all_data, readRuntimeMeasurementFile(line), stringsAsFactors=FALSE)
}
for_each_line_in_file(commandArgs(trailingOnly=TRUE)[1], collect)

overhead_data <- convertRuntimeMeasurementsToRelative(all_data)
overhead_data$value <- overhead_data$value - 100

if (debug) {
  overhead_data
}

cat(sprintf("%% Command: %s\n", paste(commandArgs(), collapse=" ")))
cat(sprintf("%%\n"))

output_to_tex(paste(csvfile, '.tex', sep=''), width=7, height=5)

xlabformatter <- function(x) {
  lab <- sprintf('%.0fk', x/1000)
}

overhead_data$catnum <- as.numeric(overhead_data$cat)

px <- pretty(overhead_data$catnum, n=14)

# ggplot(overhead_data, aes(x=alpha_sort_num(cat), y=value, shape=benchmark, color=benchmark)) +
ggplot(overhead_data, aes(x=catnum, y=value, shape=benchmark, color=benchmark)) +
  geom_point() +
  geom_text_repel(aes(label=label), show.legend=FALSE) +
  theme(axis.text.x=element_text(angle=60, hjust=1), legend.position="bottom", legend.title=element_blank()) +
  geom_hline(yintercept=0, color = "black", linetype="dashed", size=0.25) +
  scale_x_continuous(breaks=px, limits=range(px), label=xlabformatter) +
  labs( x="Number of factored fragments",
        y=sanitize_text("Overhead (%)"))

output_finish()
