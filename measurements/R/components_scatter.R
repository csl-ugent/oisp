#!/usr/bin/env Rscript
source_local <- function(fname){
    argv <- commandArgs(trailingOnly = FALSE)
    base_dir <- dirname(substring(argv[grep("--file=", argv)], 8))
    source(paste(base_dir, fname, sep="/"))
}
source_local("helpers.R")
debug <- FALSE

# INPUT = CSV file with, on each line:
# <benchmark>,<dispatcher>,<total>,<fraction>,<cat1>,<cat2>,...
args <- commandArgs(trailingOnly=TRUE)
if (length(args) == 0) {
  stop("first argument should be CSV file")
}
csvfile <- args[1]

df <- read.csv(csvfile)
df$fracX <- df$executed/df$total*100
df$fracT <- df$total/sum(df$total)*100

cat(sprintf("%% Command: %s\n", paste(commandArgs(), collapse=" ")))
cat(sprintf("%%\n"))

output_to_tex(paste(csvfile, '.tex', sep=''), width=2.5, height=2.5)

# automatisch ticks bepalen
px <- pretty(df$fracT)
py <- pretty(df$fracX)

# , expand=c(0, 0) om oorsprong echt in 0 te laten beginnen
# maar dan liggen de punten op '0' niet helemaal op de grafiek
ggplot(df, aes(x=fracT, y=fracX, shape=category)) +
  geom_point() +
  scale_shape_identity() +
  scale_x_continuous(breaks=px, limits=range(px)) +
  scale_y_continuous(breaks=py, limits=range(py)) +
  labs(x=sanitize_text("% of original program"),
       y=sanitize_text("% executed"))

caption <- sanitize_text(sprintf("%.2f%%", sum(df$executed)/sum(df$total)*100))
output_finish(caption)
