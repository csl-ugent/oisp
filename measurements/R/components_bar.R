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
df <- read.csv(csvfile, strip.white=T)
df[is.na(df)] <- 0

# only use columns that contain at least one cell!=0
df2 <- df[, colSums(df != 0) > 0]

# calculate fractions for the stacked bar chart
df2 <- data.frame(select(select(df2, -starts_with("F", ignore.case=FALSE)), -starts_with("E", ignore.case=FALSE)), df$fraction/df$total * select(df, starts_with("F", ignore.case=FALSE))/df$fraction)

# drop the 'total' and 'fraction' columns
df2 <- subset(df2, select = -c(total, fraction))

# convert data frame from 'wide' to 'long' format
df3 <- df2 %>% gather(Fraction, Data, starts_with("F", ignore.case=FALSE))

# calculate executed fractions
T <- select(df2, starts_with("F", ignore.case=FALSE))
F <- select(df, starts_with("F", ignore.case=FALSE))
E <- select(df, starts_with("E", ignore.case=FALSE))
exec_fractions <- E/F
exec_fractions[is.na(exec_fractions)] <- 0

ymax <- 1
max_frac <- max(df$fraction/df$total)
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

ncols <- length(select(df2, starts_with("F", ignore.case = FALSE)))

# random colors
#library(randomcoloR)
#cols <- distinctColorPalette(ncols)

# grey-scale colors
#cols <- gray.colors(ncols, end=0.75, gamma=0.01)

# fixed colors
cols <- c("#79BAD7", "#D591CF", "#78E6A0", "#DC555B", "#839C81", "#D8969D", "#D4E7DC", "#E3E248", "#DE61CA", "#E09E43", "#7AE5DD", "#C0D36E", "#D6C6DC", "#8369D7", "#D1EAB1", "#82E555", "#B53CE5", "#DDC095", "#7C92D3")

p <- ggplot(df3, aes(x = dispatcher, y = Data, fill = factor(Fraction, levels=rev(names(select(df2, starts_with("F", ignore.case=FALSE))))))) +
  # horizontal bars
  geom_col() + coord_flip() +
  labs(x="", y="") +
  facet_grid(benchmark ~ ., switch="y") +
  theme(strip.text.y=element_text(angle=180),
        axis.text.y=element_blank(),
        axis.ticks.y=element_blank()) +
  ylim(0, ymax) +
  scale_fill_manual(values=cols, guide=FALSE)

# init with '-1' so uninitialised values are not drawn (they are out of range)
data <- replicate(nrow(T)*ncol(T), -1)
mindata <- data
current_index <- 1
LIMIT <- 0.01
for (comp_index in 1:ncol(exec_fractions)) {
  col <- exec_fractions[, comp_index]

  for (bench_index in 1:length(col)) {
    myfrac <- exec_fractions[bench_index, comp_index] * T[bench_index, comp_index]

    if (myfrac > 0) {
      # calculate offset from start of axis
      prevtotal <- 0
      if (comp_index > 1) {
        for (prevcomp_index in 1:(comp_index-1)) {
          prevtotal <- prevtotal + T[bench_index, prevcomp_index]
        }
      }

      # only draw a line when it is not too close to the border
      if (myfrac >= LIMIT) {
        data[current_index] <- prevtotal + myfrac
        mindata[current_index] <- prevtotal
      }
    }

    current_index <- current_index + 1
  }
}
p <- p + geom_errorbar(aes(y=data, ymin=mindata, ymax=data, width=0.25))

p

output_finish()
