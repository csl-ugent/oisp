#!/usr/bin/env Rscript
source_local <- function(fname){
    argv <- commandArgs(trailingOnly = FALSE)
    base_dir <- dirname(substring(argv[grep("--file=", argv)], 8))
    source(paste(base_dir, fname, sep="/"))
}
source_local("helpers.R")
debug <- FALSE

# read input file line by line and collect the data
all_data <- data.frame(benchmark=character(), dispatcher=character(), value=numeric())

collect <- function(line) {
  # modify global variable
  all_data <<- rbind(all_data, readRuntimeMeasurementFile(line), stringsAsFactors=FALSE)
}
for_each_line_in_file(commandArgs(trailingOnly=TRUE)[1], collect)

overhead_data <- convertRuntimeMeasurementsToRelative(all_data)

if (debug) {
  overhead_data
}
overhead_data$value <- round(overhead_data$value - 100, 1)

# calculate Y-limit, in chunks of 50
ymax <- max(ceiling(overhead_data$value/100/0.5)*0.5*100)

cat(sprintf("%% Command: %s\n", paste(commandArgs(), collapse=" ")))
cat(sprintf("%%\n"))

output_to_tex(paste(csvfile, '.tex', sep=''), width=5, height=3)

geom_text_size <- 2.75

ggplot(overhead_data, aes(x = alpha_sort_num(dispatcher), y = value)) +
  geom_col() +
  facet_grid(. ~ benchmark) +
  guides(fill=guide_legend(title=NULL)) +
  theme(axis.text.x=element_text(angle=60, hjust=1)) +
  # geom_hline(yintercept=100, color = "red") +
  ylim(0, ymax) +
  scale_y_continuous(expand=expand_scale(mult=c(0, 0.3))) +
  geom_text(aes(label=value), vjust=0.5, hjust=-0.5, angle=90, size=geom_text_size) +
  labs(x="", y=sanitize_text("Overhead (%)"))

output_finish(caption="Hotness factor (1000=exclude all executed, 0=include hottest)")
