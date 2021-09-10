## Load libraries
library(Rnumerai)

## Configuration
set_public_id(Sys.getenv("NUMERAI_PUBLIC_ID"))
set_api_key(Sys.getenv("NUMERAI_SECRET_KEY"))
MODEL_ID = Sys.getenv("MODEL_ID")

## Download data
data_dir <- tempdir()
data <- download_data(data_dir)
data_train <- data$data_train
data_tournament <- data$data_tournament

############################################################
## Random Prediction || Insert your model here
############################################################
submission <- data.frame(id=data_tournament$id,prediction = sample(seq(.35,.65,by=.1),nrow(data_tournament),replace=TRUE))
############################################################
############################################################


############################################################
## Submit
############################################################
submission_id <- submit_predictions(submission,data_dir,tournament="Nomi",model_id=MODEL_ID)
############################################################
############################################################
