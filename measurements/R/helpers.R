#~/.Rprofile
#  options(repos=structure(c(CRAN="https://lib.ugent.be/CRAN")))
install_and_import <- function(req_pkg) {
  new_pkg <- req_pkg[!(req_pkg %in% installed.packages()[,"Package"])]
  if(length(new_pkg)) install.packages(new_pkg)

  for (pkg in req_pkg) {
    library(pkg, character.only = TRUE)
  }
}
install_and_import(c("dplyr", "ggplot2", "gtools", "tidyr"))

library(dplyr)
library(ggplot2)
library(gtools)
library(tidyr)

# when using Rscript
library(tcltk)
X11()

debug <- FALSE

readRuntimeMeasurementFile <- function(filepath) {
  if (debug) {
    print(filepath)
  }

  # extract and split argument
  splitted_arg <- unlist(strsplit(filepath, ':'))
  filepath <- splitted_arg[3]

  if (file.exists(filepath)) {
    # read CSV file and rename columns
    data <- read.csv(filepath, comment.char='#', header=FALSE)
    #names(data) <- c("Value", "Empty", "Measurement", "Error")
    names(data) <- c("Value", "Empty", "Measurement")

    # remote percent character and convert to numeric data type
    #data$Error <- as.numeric(sub('([0-9]+(.[0-9]+)?)%', '\\1', data$Error))

    # only look at clock times
    data$Measurement <- as.character(data$Measurement)
    clk <- data[which(startsWith(data$Measurement, 'task-clock')),]

    if (is.factor(clk$Value)) {
      clk$Value <- as.numeric(levels(clk$Value))[clk$Value]
    }

    value = mean(clk$Value)
  }
  else {
    value = as.numeric(splitted_arg[3])
  }

  # for scatter plot
  label <- ""
  if (length(splitted_arg) > 3) {
    label <- splitted_arg[4]
  }

  cat <- ""
  if (length(splitted_arg) > 4) {
    cat <- splitted_arg[5]
  }

  return(list(benchmark=splitted_arg[1], dispatcher=splitted_arg[2], value=value, label=label, cat=cat))
}

convertRuntimeMeasurementsToRelative <- function(all_data) {
  # calculate overhead in percent
  vanilla_data <- all_data[all_data$dispatcher == 'vanilla', ]
  other_data <- all_data[all_data$dispatcher != 'vanilla', ]

  overhead_data <- data.frame(benchmark=character(), dispatcher=character(), value=numeric())
  for (row in 1:nrow(vanilla_data)) {
    x <- vanilla_data[row, ]

    other_data2 <- other_data[other_data$benchmark == x$benchmark, ]
    for (row2 in 1:nrow(other_data2)) {
      y <- other_data2[row2, ]
      y$value <- y$value / x$value * 100
      overhead_data <- rbind(overhead_data, y)
    }
  }

  return(overhead_data)
}

waitForInput <- function() {
  prompt <- "press [SPACE] to close plots"
  extra <- ""
  capture <- tk_messageBox(message = prompt, detail = extra)
}

for_each_line_in_file <- function(filename, fun) {
  con = file(filename, "r")
  while ( TRUE ) {
    line = readLines(con, n = 1)
    if (length(line) == 0) {
      break
    }

    fun(line)
  }
  close(con)
}

alpha_sort_num <- function(data) {
  return(factor(data, level = as.character(sort(as.numeric(levels(factor(data)))))))
}

already_sorted <- function(data) {
  return(factor(data, level = levels(factor(data))))
}

output_to_tex <- function(f, width, height) {
  if (debug) {
    # do nothing
  }
  else {
    if (missing(width)) {
      width <- 5
    }
    if (missing(height)) {
      height <- 2
    }

    install_and_import("tikzDevice")
    tikz(console=TRUE, width=width, height=height, standAlone=FALSE)
  }
}

output_finish <- function(caption) {
  if (debug) {
    prompt <- "press [SPACE] to close plots"
    extra <- ""
    capture <- tk_messageBox(message = prompt, detail = extra)
  }
  else {
    dummy <- dev.off()

    if (!missing(caption)) {
      cat(sprintf("\\gdef\\rcaption{%s}\n", caption))
    }
  }
}

sanitize_text <- function(str) {
  if (debug) {
    return(str)
  }
  else {
    return(sanitizeTexString(str))
  }
}

readcsv <- function(csvfile) {
  fieldcount <- max(count.fields(csvfile, comment.char='#', sep=','))

  df <- read.csv(csvfile, header=FALSE, comment.char='#', col.names=c(1:fieldcount))
  df[is.na(df)] <- 0

  return(df)
}