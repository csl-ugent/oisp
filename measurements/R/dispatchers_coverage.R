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

# read CSV file and replace NA (empty) values with 0
df <- readcsv(csvfile)
# rename the columns
names(df) <- c('benchmark', 'dispatcher', 'total', 'factored', c(sprintf('X%d', 0:(ncol(df) - 4 - 1))))
# only use columns that contain at least one cell!=0
df <- df[, colSums(df != 0) > 0]

# calculate fractions for the stacked bar chart
df2 <- data.frame(df[c(1:2)], df$factored/df$total * df[5:ncol(df)]/df$factored)

# convert data frame from 'wide' to 'long' format
df3 <- df2 %>% gather(Fraction, Data, 3:ncol(df2))

ymax <- 1
max_frac <- max(df$factored/df$total)
if (max_frac < 0.75) {
  ymax <- 0.75
}
if (max_frac < 0.5) {
  ymax <- 0.5
}
if (max_frac < 0.25) {
  ymax <- 0.25
}

# plot the data

cat(sprintf("%% Command: %s\n", paste(commandArgs(), collapse=" ")))
cat(sprintf("%% Source data: %s\n", csvfile))
cat(sprintf("%%\n"))

output_to_tex(paste(csvfile, '.tex', sep=''), width=5, height=2)

ncols <- length(select(df, starts_with("X")))

# already sorted, don't do it for us
df3$dispatcher <- factor(df3$dispatcher, levels=unique(df3$dispatcher), ordered = TRUE)

# fixed colors
cols <- c("X0"="#79BAD7", "X1"="#D591CF", "X2"="#78E6A0", "X3"="#DC555B", "X4"="#839C81", "X5"="#D8969D", "X6"="#D4E7DC", "X7"="#E3E248", "X8"="#DE61CA", "X9"="#E09E43", "X10"="#7AE5DD", "X11"="#C0D36E", "X12"="#D6C6DC", "X13"="#8369D7", "X14"="#D1EAB1", "X15"="#82E555", "X16"="#B53CE5", "X17"="#DDC095", "X18"="#7C92D3", "X19"="#FF0000", "X20"="#00FF00")

labels <- c('variable', 'quasi-invariant', 'not covered')
order <- c('X0', 'X1', 'X2')

ggplot(df3, aes(x = dispatcher, y = Data, fill = factor(Fraction, levels=rev(names(df2[3:ncol(df2)]))))) +
  geom_col() +
  labs(x="", y="") +
  facet_grid(. ~ benchmark) +
  theme(axis.text.x = element_blank(), legend.box.margin=margin(-20,0,0,0), legend.position="bottom", legend.box = "horizontal", legend.spacing.x = unit(0.25, "line"), legend.spacing.y = unit(0, "cm"), legend.title=element_blank()) +
  scale_fill_manual(guide=guide_legend(title="", direction="horizontal", label.position="right", label.theme=element_text(angle=0, size=8, hjust=0), keywidth=unit(0.5, "line"), keyheight=unit(0.5, "line"), reverse=TRUE), values=cols, labels=labels, breaks=order) +
  scale_y_continuous(expand=expand_scale(c(0, 0.05)), limits=c(0, ymax))

output_finish()
