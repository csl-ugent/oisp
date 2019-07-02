#!/usr/bin/env Rscript
source_local <- function(fname){
    argv <- commandArgs(trailingOnly = FALSE)
    base_dir <- dirname(substring(argv[grep("--file=", argv)], 8))
    source(paste(base_dir, fname, sep="/"))
}
source_local("helpers.R")
debug <- FALSE

# INPUT = CSV file with, on each line:
args <- commandArgs(trailingOnly=TRUE)
if (length(args) == 0) {
  stop("first argument should be CSV file")
}
csvfile <- args[1]

df <- readcsv(csvfile)

max_average <- 0
max_stdev <- 0
for (i in levels(df$X1)) {
  subdf <- df[which(df$X1==i), ]

  avg <- mean(subdf$X3)
  dev <- sd(subdf$X3)
  cat(sprintf("%s AVERAGE(%f) STDEV(%f)\n", i, avg, dev))

  if (avg > max_average)
    max_average <- avg
  if (dev > max_stdev)
    max_stdev <- dev
}

cat(sprintf("max. average: %f\n", max_average))
cat(sprintf("max. stdev  : %f\n", max_stdev))
