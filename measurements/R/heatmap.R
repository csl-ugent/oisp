#!/usr/bin/env Rscript
source_local <- function(fname){
    argv <- commandArgs(trailingOnly = FALSE)
    base_dir <- dirname(substring(argv[grep("--file=", argv)], 8))
    source(paste(base_dir, fname, sep="/"))
}
source_local("helpers.R")
install_and_import(c("ggnewscale", "cowplot", "gridExtra", "grid"))

args <- commandArgs(trailingOnly=TRUE)
if (length(args) == 0) {
  stop("first argument should be CSV file")
}
csvfile <- args[1]

# don't draw a legend by default
legendposition <- 'none'

debug <- TRUE
if (debug) {
  legendposition <- 'right'
}

legend_only <- TRUE
if (length(args) >= 2) {
  legend_only <- as.logical(args[2])
}
if (legend_only) {
  legendposition <- 'right'
}

df <- read.csv(csvfile, strip.white=T, comment.char='#')
df[is.na(df)] <- 0

# only use columns that contain at least one cell!=0
df <- df[, colSums(df != 0) > 0]

df <- df[rowSums(select(df, starts_with("X")) != 0) > 0, ]

# flatten the data frame from 'wide' to 'long'
df2 <- gather(df, X, Value, starts_with("X"))

# positions at which to draw vertical lines
data_column_idx <- grep("^X", names(df))
x <- sub("\\.[0-9]+", "", names(df)[data_column_idx])
vertical_lines <- data_frame(xvalues=seq_along(x)[!duplicated(x)]-0.5)

# replace NA with 0
df2[is.na(df2)] <- 0

# min/max
minv <- min(df2$Value[df2$Value > 0])
maxv <- max(df2$Value[df2$Value > 0])

df2$X <- factor(df2$X, levels=unique(df2$X))

cat(sprintf("%% Command: %s\n", paste(commandArgs(), collapse=" ")))
cat(sprintf("%% Source data: %s\n", csvfile))
cat(sprintf("%%\n"))

# Y axis: ticks
yticks = c(min(df2$Y):max(df2$Y))

# X axis: labels
lengths <- sub("^X[0-9]+\\.", "", names(df)[data_column_idx])
ncomps <- sub("^X", "", sub("\\.[0-9]+", "", names(df)[data_column_idx]))
prev <- ncomps[1]
for (idx in 2:length(ncomps)) {
  if (ncomps[idx] == prev) {
    ncomps[idx] = ""
  }
  else {
    prev = ncomps[idx]
  }
}
labels <- paste0(lengths, "\n", ncomps)

quant <- as.vector(quantile(unique(sort(df2$Value)), c(0.25, 0.50, 0.75)))

l1 <- minv
u1 <- quant[1]
l2 <- u1+1
u2 <- quant[2]
l3 <- u2+1
u3 <- quant[3]
l4 <- u3+1
u4 <- maxv

# We do this to generate consistently sized heatmnaps.
# Using the kruler Linux tool, we:
#  (1) measure the width in pixels of one page: A; we know that a page is 8.5 in wide
#      -> A/B = C px/in
#  (2) we know that, for the SLM a good width value (in inches) supplied here is '6'.
#      -> C*6 = D px total width for the SLM.
#  (3) Using the kruler tool, we measure the width in px of one square in the heatmap: E px.
#  (4) The total width of the heatmap itself is E*N, where 'N' is the number of horizontally placed squares.
#      -> extra px introduced for labels etc is: D - E*N.
#  To calculate the correct width (in 'in'):
#  WIDTH(SLM)/PX(SLM) * (PADDING + N*E)
calculated_width <- 6/826 * (44 + length(lengths)*17)
output_to_tex(paste(csvfile, '.tex', sep=''), width=calculated_width, height=2.5)

add_part <- function(order, p, alldata, L, U, colors, title) {
  alldata[(alldata$Value < L) | (U < alldata$Value), ]$Value <- NA
  alldata$Value <- as.factor(alldata$Value)
  Acol <- colorRampPalette(colors, space="Lab")(length(levels(alldata$Value)))

  return(
    p +
    new_scale("fill") +
    geom_tile(aes(fill=Value), data = alldata) +
    scale_fill_manual(guide=guide_legend(title=title, direction="horizontal", label.position="bottom", nrow=1, label.theme=element_text(angle=90, size=8, hjust=1, margin=margin(t=3)), keywidth=unit(0.5, "line"), keyheight=unit(0.5, "line"), order=order), values=Acol, breaks=levels(alldata$Value)) +
    theme(legend.position="none")
  )
}

p <- ggplot(df2, aes(x=X, y=Y))

hue_m = 0
hue_M = 225/360

hue_delta = (hue_M - hue_m)/4

# HSV base
p <- add_part(1, p, df2, l1, u1, c(hsv(hue_M - 0*hue_delta, 1, 1), hsv(hue_M - 1*hue_delta, 1, 1)), "")
p <- add_part(2, p, df2, l2, u2, c(hsv(hue_M - 1*hue_delta, 1, 1), hsv(hue_M - 2*hue_delta, 1, 1)), "")
p <- add_part(3, p, df2, l3, u3, c(hsv(hue_M - 2*hue_delta, 1, 1), hsv(hue_M - 3*hue_delta, 1, 1)), "")
p <- add_part(4, p, df2, l4, u4, c(hsv(hue_M - 3*hue_delta, 1, 1), hsv(hue_M - 4*hue_delta, 1, 1)), "")

plot <- p +
  labs(x="", y="covered archives") +
  # keep aspect ratio: 1 X-unit = 1 Y-unit
  coord_fixed() +
  # Y-axis has discrete values
  scale_y_discrete(expand=c(0,0), limits=yticks, breaks=yticks) +
  scale_x_discrete(labels=labels) +
  theme_grey(base_size=10) +
  # rotate X-axis labels
  theme(axis.text.x=element_text(hjust=0.5), axis.title.x=element_blank(), legend.spacing.x = unit(0, "cm"), legend.spacing.y = unit(0, "cm"), legend.position=legendposition, legend.box="vertical") +
  guides(color=guide_legend(nrow=2)) +
  # vertical lines
  geom_vline(data=vertical_lines, aes(xintercept=xvalues), size=0.25)

# helper to extract legend from a plot
g_legend<-function(plt) {
  tmp <- ggplot_gtable(ggplot_build(plt))
  leg <- which(sapply(tmp$grobs, function(x) x$name) == "guide-box")
  legend <- tmp$grobs[[leg]]
  return(legend)
}

if (legend_only) {
  legend <- g_legend(plot)
  grid.newpage()
  grid.draw(legend)
} else {
  plot
}

# plot_grid(plot, legend, nrow=2)

caption <- ""
output_finish(caption)
