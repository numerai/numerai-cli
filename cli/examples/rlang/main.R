## Load libraries
library(Rnumerai)
library(pROC)
library(mxnet)

## Configuration
set_public_id(Sys.getenv("NUMERAI_PUBLIC_ID"))
set_api_key(Sys.getenv("NUMERAI_SECRET_KEY"))

## Download data
data_dir <- tempdir()
data <- download_data(data_dir)
data_train <- data$data_train
data_tournament <- data$data_tournament

############################################################
## Mxnet
############################################################

## Partition the data
train.x = data.matrix(data_train[,4:53])
test.x = data.matrix(data_tournament[, 4:53])
val.x = data.matrix(data_tournament[data_tournament$data_type=="validation", 4:53])

## Define tournament parameters
tournament_idx <- c(54,57:60)
predictions_mxnet <- list()
auc_train_mxnet <- numeric()
auc_val_mxnet <- numeric()

## Fit models
for(idx in 1:length(tournament_idx))
{
    train.y = data_train[, tournament_idx[idx]]
    val.y = c(data_tournament[data_tournament$data_type=="validation", tournament_idx[idx]])

    mx.set.seed(0)
    model <- mx.mlp(train.x,
                    train.y,
                    hidden_node=25,
                    out_node=2,
                    out_activation="softmax",
                    num.round=5000,
                    array.batch.size=10000,
                    learning.rate=.1,
                    momentum=0.05,
                    eval.metric=mx.metric.accuracy,
                    ctx=mx.cpu(),
                    eval.data = list(data = val.x, label = val.y),
                    epoch.end.callback = mx.callback.early.stop(maximize=TRUE,bad.steps = 100)
                )
    pr_train <- predict(model, train.x)[2,]
    pr_val <- predict(model, val.x)[2,]
    auc_train_mxnet[idx] <- auc(roc(train.y, pr_train, algorithm = 2))
    auc_val_mxnet[idx] <- auc(roc(val.y, pr_val, algorithm = 2))
    predictions_mxnet[[idx]] <- predict(model, test.x)[2,]
}
############################################################
############################################################


############################################################
## Submit
############################################################
submissions <- list()
for(idx in 1:length(tournament_idx))
{
	submissions[[idx]] <- data.frame(id=data_tournament$id,probability=(predictions_mxnet[[idx]]))
}
names(submissions) <- c("Bernie","Ken","Charles","Frank","Hillary")
submission_ids <- submit_predictions_multi(submissions,data_dir)

## Wait for the concordance to be calculated for every submission
# Sys.sleep(300)

## Stake .1 NMR on every submission
# stake_nmr_multi(tournaments=c("Bernie","Ken","Charles","Frank","Hillary"),values = c(.1,.1,.1,.1,.1), confidence_vals = rep(.7,5))
############################################################
############################################################
