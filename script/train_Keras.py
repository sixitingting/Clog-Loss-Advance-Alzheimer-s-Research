# The Code written by Ali Babolhaveji @ 6/9/2020


import sys
import yaml
from tqdm import tqdm
import os
import gc
import pandas as pd

os.environ["CUDA_VISIBLE_DEVICES"]="0,1,2,3"

package_path = '..'
# package_path = '../../script2/Result/nuScenes/exp3/sources/'
if not package_path in sys.path:
    sys.path.append(package_path)

from Klib import  DataSet


config = './config.yml'
with open (config , 'rb') as f:
    config = yaml.load(f ,Loader=yaml.FullLoader)

# print(config)
dataset = DataSet(config)



# for data in tqdm(dataset.data_generator(dataset.df_dataset,batch_size=10)):
#     print(data[0].shape ,data[1].shape)



from keras.preprocessing import sequence
from keras.models import Sequential
from keras.layers import *
from keras.layers import LSTM
from keras.datasets import imdb


from keras.utils import multi_gpu_model
from keras.optimizers import Adam, SGD
from keras import backend as K
from keras import models
import tensorflow as tf
import keras.backend.tensorflow_backend as tfback

from keras.callbacks import ModelCheckpoint

# physical_devices = tf.config.experimental.list_physical_devices('GPU')
# for physical_device in physical_devices:
#     tf.config.experimental.set_memory_growth(physical_device, True)








data = DataSet(config)
X_train, X_test, y_train, y_test = data.split_train_test()
# X_test = data.df_dataset


print("tf.__version__ is", tf.__version__)
print("tf.keras.__version__ is:", tf.keras.__version__)
#
def _get_available_gpus():
    """Get a list of available gpu devices (formatted as strings).

    # Returns
        A list of available GPU devices.
    """
    #global _LOCAL_DEVICES
    if tfback._LOCAL_DEVICES is None:
        devices = tf.config.list_logical_devices()
        tfback._LOCAL_DEVICES = [x.name for x in devices]
    return [x for x in tfback._LOCAL_DEVICES if 'device:gpu' in x.lower()]


tfback._get_available_gpus = _get_available_gpus

#tf.config.experimental_list_devices()
print(tf.config.list_logical_devices())







# checkpoint
filepath="weights-improvement-{epoch:02d}-{val_accuracy:.2f}.hdf5"
checkpoint = ModelCheckpoint(filepath, monitor='val_accuracy', verbose=1, save_best_only=True, mode='max')
callbacks_list = [checkpoint]

# checkpoint
filepath="weights-improvement-{epoch:02d}-{val_accuracy:.2f}.hdf5"

def focal_loss(gamma=2., alpha=.25):
	def focal_loss_fixed(y_true, y_pred):
		pt_1 = tf.where(tf.equal(y_true, 1), y_pred, tf.ones_like(y_pred))
		pt_0 = tf.where(tf.equal(y_true, 0), y_pred, tf.zeros_like(y_pred))
		return -K.mean(alpha * K.pow(1. - pt_1, gamma) * K.log(pt_1)) - K.mean((1 - alpha) * K.pow(pt_0, gamma) * K.log(1. - pt_0))
	return focal_loss_fixed

batch_size = 32
epochs = 100
size = (224, 224)

train_steps = len(X_train) / batch_size
valid_steps = len(X_test) / batch_size

weights_path = "/home/mjamali/proj/B/Clog/script/result_6th/weights-improvement-08-0.97.hdf5"   # -->5
# model = models.load_model(weights_path).save("my_h5_model.h5")


def get_model():

    # with strategy.scope():
    model = Sequential()
    model.add(TimeDistributed(Conv2D(32, (7, 7), strides=(2, 2), activation='relu', padding='same'),
                              input_shape=(100, 224, 224, 1)))
    model.add(TimeDistributed(Conv2D(32, (3, 3), kernel_initializer="he_normal", activation='relu')))
    model.add(TimeDistributed(MaxPooling2D((2, 2), strides=(2, 2))))

    model.add(TimeDistributed(Conv2D(64, (3, 3), padding='same', activation='relu')))
    model.add(TimeDistributed(Conv2D(64, (3, 3), padding='same', activation='relu')))
    model.add(TimeDistributed(MaxPooling2D((2, 2), strides=(2, 2))))

    model.add(TimeDistributed(Conv2D(128, (3, 3), padding='same', activation='relu')))
    model.add(TimeDistributed(Conv2D(128, (3, 3), padding='same', activation='relu')))
    model.add(TimeDistributed(MaxPooling2D((2, 2), strides=(2, 2))))

    model.add(TimeDistributed(Conv2D(256, (3, 3), padding='same', activation='relu')))
    model.add(TimeDistributed(Conv2D(256, (3, 3), padding='same', activation='relu')))
    model.add(TimeDistributed(MaxPooling2D((2, 2), strides=(2, 2))))

    model.add(TimeDistributed(Conv2D(512, (3, 3), padding='same', activation='relu')))
    model.add(TimeDistributed(Conv2D(512, (3, 3), padding='same', activation='relu')))
    model.add(TimeDistributed(MaxPooling2D((2, 2), strides=(2, 2))))

    model.add(TimeDistributed(Flatten()))

    model.add(Dropout(0.4))
    model.add(LSTM(256, return_sequences=False, dropout=0.4))
    model.add(Dense(2, activation='sigmoid'))
    return model

strategy = tf.distribute.MirroredStrategy()
with strategy.scope():

    model = get_model()
    parallel_model = multi_gpu_model(model, gpus=4)

    parallel_model.load_weights('my_h5_model.h5')
    parallel_model.compile(optimizer=Adam(lr=0.00001), loss='binary_crossentropy', metrics=['accuracy'])
parallel_model.fit_generator(data.data_generator(X_train, 'standard', size=size, batch_size=batch_size),
                                 train_steps, epochs=epochs, callbacks=callbacks_list, verbose=1,
                                 validation_data=data.data_generator(X_test, 'standard', size=size,
                                                                     batch_size=batch_size),
                                 validation_steps=valid_steps, workers=39,
                                 initial_epoch=2)  # ,use_multiprocessing= True)




# model = model.load_weights(weights_path )
# parallel_model.compile(optimizer=Adam(lr=0.00001), loss='binary_crossentropy', metrics = ['accuracy'])
# #parallel_model.compile(optimizer=Adam(lr=0.0001), loss=[focal_loss(alpha=.25, gamma=2)],metrics = ['accuracy'])
#
# parallel_model.fit_generator(data.data_generator(X_train, 'standard', size=size, batch_size=batch_size),
#                     train_steps, epochs=epochs, callbacks=callbacks_list, verbose=1,
#                     validation_data=data.data_generator(X_test, 'standard', size=size, batch_size=batch_size),
#                     validation_steps=valid_steps , workers=39 ,initial_epoch=2)#,use_multiprocessing= True)

# model.compile(optimizer=Adam(lr=0.0001), loss='categorical_crossentropy', metrics=['accuracy'])
#
# model.fit_generator(data.data_generator(X_train, 'standard', size=size, batch_size=batch_size),
#                     train_steps, epochs=epochs, verbose=1,
#                     validation_data=data.data_generator(X_test, 'standard', size=size, batch_size=batch_size),
#                     validation_steps=valid_steps)
