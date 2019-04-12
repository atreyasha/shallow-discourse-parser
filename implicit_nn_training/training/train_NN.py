#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
import pickle
from keras.models import Model
from keras.layers import Dense, LSTM, Dropout, Input, SpatialDropout1D
from keras.callbacks import EarlyStopping
from keras.regularizers import l2 # for keras 2
from keras.utils import np_utils, plot_model
from keras import optimizers
from training import metrics as met
import warnings
warnings.filterwarnings('ignore')
# TODO: Implement own f1

def evaluate_model(model, data):
    evaluation = []
    for x, y in data:
        y_true = np.argmax(y, axis = 1)
        y_pred = np.argmax(model.predict(x), axis = 1)
        acc = accuracy_score(y_true, y_pred)
        rec = recall_score(y_true, y_pred, average="weighted")
        prec = precision_score(y_true, y_pred, average="weighted")
        f1 = f1_score(y_true, y_pred, average="weighted")
        evaluation.append((acc, rec, prec, f1))


def create_model(depth, hidden_nodes, activation_hidden, activation_output, output_shape,
                input_shape, drop = True):
    """Creates the model based on inputs. Nothing special just cleanup"""
    inlayer = Input((input_shape,))
    if depth == 1:
        output = Dense(output_shape, activation = activation_output)(inlayer)
        model = Model(inputs = inlayer, outputs = output)
        return model
    elif depth == 2:
        hidden = Dense(hidden_nodes, activation = activation_hidden)(inlayer)
        if drop:
            drop = Dropout(0.5)(hidden)
            output = Dense(output_shape, activation = activation_output)(drop)
        else:
            output = Dense(output_shape, activation = activation_output)(hidden)
        model = Model(inputs = inlayer, outputs = output)
        return model
    elif depth == 3:
        hidden = Dense(hidden_nodes, activation = activation_hidden)(inlayer)
        hidden2 = Dense(hidden_nodes, activation = activation_hidden)(hidden)
        output = Dense(output_shape, activation = activation_output)(hidden2)
        model = Model(inputs = inlayer, outputs = output)
        return model

    
def create_optimizer(method, learning_rate, momentum, decay):
    """Creates the optimizing function based on training arguments"""
    if method == "nag":
        return optimizers.SGD(lr = learning_rate, momentum=momentum, decay = decay, nesterov = True)
    elif method == "sgd":
        return optimizers.SGD(lr = learning_rate, momentum=momentum, decay = decay)
    elif method == "adam":
        return optimizers.adam(lr = learning_rate)
    else:
        return optimizers.adam(lr = learning_rate)

def train_theanet(method, learning_rate, momentum, decay, regularization, hidden,
                  min_improvement, validate_every, patience, weight_lx, hidden_lx,
                  embeddings, direct, name = 0, depth = 2):
    ''' train neural network, calculate confusion matrix, save neural network'''
    #input_train, output_train, input_dev, output_dev, input_test, output_test, label_subst = embeddings
    train, dev, test, label_subst = (embeddings[0], embeddings[1]), (embeddings[2], embeddings[3]), (embeddings[4], embeddings[5]), embeddings[6] # repackaging 

    ## Training options:
    ## 1.) use 90% training set to train, use remaining 10% to validate, use test set to test
    #split_point = int(len(input_train)*0.9)
    #train_data = (input_train[:split_point], output_train[:split_point])
    #valid_data = (input_train[split_point:], output_train[split_point:])
    #test_data = (input_dev, output_dev)
    ## 2.) use 100% training set to train, use test set to validate and to test
    train_accs, dev_accs, test_accs = [], [], []
    train_recs, dev_recs, test_recs = [], [], []
    train_precs, dev_precs, test_precs = [], [], []
    train_f1, dev_f1, test_f1 = [], [], []
    
    accs = []
    f1s = []
    precs = []
    recs = []
    train[1] = np_utils.to_categorical(train[1], num_classes=None)

    # print(input_train.shape)
    # print(len(input_train[0]))
    # print(output_train.shape)
    # print(np.argmax(output_train, axis = 1))
    num_classes = output_train.shape[1]
    dev[1] = np_utils.to_categorical(dev[1], num_classes=num_classes)
    test[1] = np_utils.to_categorical(test[1], num_classes=num_classes) 
    
    for nexp in range(1):
        best_acc, best_f1, best_prec, best_rec = 0, 0, 0, 0
        #inlayer = Input((input_dev.shape[1],))
        # TODO: regularization
        # TODO: hidden
        # TODO: weight lx
        # TODO: hiddenlx
        model = create_model(2, hidden[0], hidden[1], 'softmax', num_classes, input_train.shape[1])
        opt = create_optimizer(method, learning_rate, momentum, decay)
        
        # Early stopping monitors the development of loss and aborts the training if it starts
        # to increase again (prevents overfitting)
        es = EarlyStopping(monitor='acc',
                        patience=patience,
                        mode='min',
                        min_delta = min_improvement,
                        verbose=0)

        model.compile(loss='categorical_crossentropy', 
                    optimizer=opt, 
                    metrics=['accuracy'])
        for epoch in range(50):
            _ = model.fit(input_train, output_train, 
                        epochs = epoch +1, 
                        batch_size = 80,
                        validation_data = (input_dev, output_dev),
                        verbose = 0,
                        callbacks = [es],
                        initial_epoch = epoch)
            if epoch % validate_every == 0: # TODO: this is wrong right?
                print("\ttrain\tdev\ttest")
                # scores are loss, acc, f1, recall, precision
                train_scores = model.evaluate(train[0], train[1], verbose = 0, batch_size=80)
                print("acc.\t%.2f%%" % (train_scores[1]*100), end="", flush=True)
                dev_scores = model.evaluate(dev[0], dev[1], batch_size = 80, verbose = 0)
                print("\t%.2f%%" % (dev_scores[1]*100), end="", flush=True)
                test_scores = model.evaluate(test[0], test[1], verbose=0, batch_size= 80)
                print("\t%.2f%%" % (test_scores[1]*100), flush=True)

        # Done training, now compute acc, prec etc which only makes sense after training.
        y_pred = model.predict(input_dev)
        y_pred = np.argmax(y_pred, axis=1)
        y_true = np.argmax(output_dev, axis = 1)
        print("Final\tAcc\tRec\tPrec\tF1")
        acc = accuracy_score(y_true, y_pred)
        rec = recall_score(y_true, y_pred, average='weighted')
        prec = precision_score(y_true, y_pred, average='weighted')
        f1 = f1_score(y_true, y_pred, average='weighted')
        print("\t%.4f\t%.4f\t%.4f\t%.4f" % (acc, rec, prec, f1))
        accs.append(acc)
        recs.append(rec)
        precs.append(prec)
        f1s.append(f1)
        del model # Reset

    # confmx = confusion_matrix(exp.network.predict(test_data[0]), test_data[1])
    # acc = float(sum(np.diag(confmx)))/sum(sum(confmx))
    # report = classification_report(exp.network.predict(test_data[0]),test_data[1])
    # accs.append(acc)
    # train_acc = accuracy_score(exp.network.predict(train_data[0]),train_data[1])
    # train_accs.append(train_acc)
    # valid_acc = accuracy_score(exp.network.predict(valid_data[0]),valid_data[1])
    # valid_accs.append(valid_acc)
    # file = open("pickles/"+str(direct)+"/neuralnetwork_"+str(name)+".pickle", "wb")
    # pickle.dump(exp.network, file, protocol=pickle.HIGHEST_PROTOCOL)
    # file.close()
    return np.average(accs),0,0,0,np.average(recs),np.average(precs),np.average(f1s)
    # return np.average(accs), np.average(valid_accs), np.average(train_accs), report
