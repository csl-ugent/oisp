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

df <- read.csv(args[1], header=FALSE, comment.char='#')
names(df) <- c('category', 'X', 'Y')
df$Y <- df$Y*100

cat(sprintf("%% Command: %s\n", paste(commandArgs(), collapse=" ")))
cat(sprintf("%%\n"))

output_to_tex(paste(csvfile, '.tex', sep=''), width=2.52, height=2.5)

# automatisch ticks bepalen
px <- pretty(df$X)
py <- pretty(df$Y)

# , expand=c(0, 0) om oorsprong echt in 0 te laten beginnen
# maar dan liggen de punten op '0' niet helemaal op de grafiek
ggplot(df, aes(x=X, y=Y, color=category)) +
  geom_point() +
  geom_line() +
  theme(legend.box.margin=margin(-20,0,0,0), legend.position="bottom", legend.box = "horizontal", legend.spacing.x = unit(0, "cm"), legend.spacing.y = unit(0, "cm"), legend.title=element_blank()) +
  scale_x_continuous(breaks=px, limits=range(px)) +
  scale_y_continuous(expand=c(0, 0.05), breaks=c(0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100), limits=range(0, 100)) +
  labs(x=sanitize_text("cycle size"),
       y=sanitize_text("false rate %"))

output_finish()
