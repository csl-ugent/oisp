#!/usr/bin/env Rscript
source_local <- function(fname){
    argv <- commandArgs(trailingOnly = FALSE)
    base_dir <- dirname(substring(argv[grep("--file=", argv)], 8))
    source(paste(base_dir, fname, sep="/"))
}
source_local("helpers.R")
debug <- TRUE

# INPUT = CSV file with, on each line:
# <benchmark>,<dispatcher>,<total>,<fraction>,<cat1>,<cat2>,...
args <- commandArgs(trailingOnly=TRUE)
if (length(args) == 0) {
  stop("first argument should be CSV file")
}

df <- data.frame(size=numeric(), fraction=numeric(), category=character(), label=character())
dfmean <- data.frame(value=numeric(), category=character(), stringsAsFactors=FALSE)

for (i in seq(1, length(args), by=2)) {
  csvfile <- args[i]
  dataset <- args[i+1]

  subdf <- read.csv(csvfile)

  # collect mean data
  mean <- weighted.mean(subdf$fraction_drawn_fake, subdf$function_count)*100
  dfmean[nrow(dfmean)+1, ] = list(mean, dataset)

  # collect scatter data
  scatter <- select(subdf, function_size, fraction_drawn_fake)
  names(scatter) <- c('size', 'fraction')
  scatter$category <- dataset
  scatter$label <- sprintf('%s (%.2f%%)', dataset, mean)

  df <- rbind(df, scatter)
}

df$fraction <- df$fraction*100

cat(sprintf("%% Command: %s\n", paste(commandArgs(), collapse=" ")))
cat(sprintf("%%\n"))

output_to_tex(paste(csvfile, '.tex', sep=''), width=7, height=5)

# automatisch ticks bepalen
py <- pretty(df$fraction)

# , expand=c(0, 0) om oorsprong echt in 0 te laten beginnen
# maar dan liggen de punten op '0' niet helemaal op de grafiek
ggplot(df, aes(x=size, y=fraction, color=factor(df$label, levels=unique(df$label)))) +
  geom_hline(aes(yintercept=as.numeric(value), color=factor(unique(df$label), levels=unique(df$label))), dfmean) +
  geom_point() +
  theme(legend.title=element_blank()) +
  scale_x_continuous(trans='log10') +
  scale_y_continuous(breaks=py, limits=range(py)) +
  labs(x=sanitize_text("function size (# BBLs)"),
       y=sanitize_text("% drawn fake edges"))

output_finish()
