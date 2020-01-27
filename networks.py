import threading
import numpy as np
import tensorflow as tf
from tensorflow.compat.v1 import Session
from tensorflow.compat.v1 import get_default_graph
from tensorflow.compat.v1.keras.backend import set_session
from tensorflow.compat.v1.keras.models import Model, Sequential
from tensorflow.compat.v1.keras.layers import Input, Activation, Dense, LSTM, Conv2D, BatchNormalization, Dropout, MaxPooling2D, Flatten
from tensorflow.compat.v1.keras.optimizers import SGD


class Network:
    lock = threading.Lock()
    sess = Session()
    graph = get_default_graph()

    def __init__(self, input_dim=0, output_dim=0, lr=0.01, 
                shared_network=None, activation='linear'):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.lr = lr
        self.model = None
        self.shared_network = shared_network
        self.activation = activation

    def predict(self, sample):
        with self.lock:
            with self.graph.as_default():
                set_session(self.sess)
                self.prob = self.model.predict(sample).flatten()
        return self.prob

    def train_on_batch(self, x, y):
        loss = 0.
        with self.lock:
            with self.graph.as_default():
                set_session(self.sess)
                loss = self.model.train_on_batch(x, y)
        return loss

    def save_model(self, model_path):
        if model_path is not None and self.model is not None:
            self.model.save_weights(model_path, overwrite=True)

    def load_model(self, model_path):
        if model_path is not None:
            self.model.load_weights(model_path)

    @classmethod
    def get_shared_network(cls, net='lstm', n_steps=1, input_dim=0, sess=None, graph=None):
        with cls.graph.as_default():
            set_session(cls.sess)
            if net == 'dnn':
                return DNN.get_network_head(Input((input_dim,)))
            elif net == 'lstm':
                return LSTMNetwork.get_network_head(Input((n_steps, input_dim)))
            elif net == 'cnn':
                return CNN.get_network_head(Input((n_steps, input_dim)))


class DNN(Network):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        inp = Input((self.input_dim,))
        if self.shared_network is None:
            output = self.get_network_head(inp).output
        else:
            output = self.shared_network.output
        output = Dense(self.output_dim, activation=self.activation)(output)
        self.model = Model(inp, output)
        self.model.compile(optimizer=SGD(lr=self.lr), loss='mse')

    @staticmethod
    def get_network_head(inp):
        output = Dense(128, activation='linear')(inp)
        output = Dropout(0.1)(output)
        output = Dense(128, activation='linear')(output)
        output = Dropout(0.1)(output)
        output = Dense(128, activation='linear')(output)
        output = Dropout(0.1)(output)
        return Model(inp, output)

    def train_on_batch(self, x, y):
        x = np.array(x).reshape((-1, self.input_dim))
        return super().train_on_batch(x, y)

    def predict(self, sample):
        sample = np.array(sample).reshape((1, self.input_dim))
        return super().predict(sample)
    

class LSTMNetwork(Network):
    def __init__(self, *args, n_steps=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.n_steps = n_steps
        inp = Input((self.n_steps, self.input_dim))
        output = None
        if self.shared_network is None:
            output = self.get_network_head(inp).output
        else:
            output = self.shared_network.output
        output = Dense(self.output_dim)(output)
        output = Activation(self.activation)(output)
        self.model = Model(inp, output)
        self.model.compile(optimizer=SGD(lr=self.lr), loss='mse')

    @staticmethod
    def get_network_head(inp):
        output = LSTM(128, dropout=0.1, return_sequences=True)(inp)
        output = LSTM(128, dropout=0.1)(output)
        return Model(inp, output)

    def train_on_batch(self, x, y):
        x = np.array(x).reshape((-1, self.n_steps, self.input_dim))
        return super().train_on_batch(x, y)

    def predict(self, sample):
        sample = np.array(sample).reshape((1, self.n_steps, self.input_dim))
        return super().predict(sample)


class CNN(Network):
    def __init__(self, *args, n_steps=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.n_steps = n_steps
        inp = Input((1, self.n_steps, self.input_dim))
        if self.shared_network is None:
            output = self.get_network_head(inp).output
        else:
            output = self.shared_network.output
        output = Dense(self.output_dim)(output)
        output = Activation(self.activation)(output)
        self.model = Model(inp, output)
        self.model.compile(optimizer=SGD(lr=self.lr), loss='mse')

    @staticmethod
    def get_network_head(inp):
        output = Conv2D(128, kernel_size=(1, 3))(inp)
        output = MaxPooling2D(pool_size=(1, 2))(output)
        output = Dropout(0.1)(output)
        output = Flatten()(output)
        return Model(inp, output)

    def train_on_batch(self, x, y):
        x = np.array(x).reshape((-1, 1, self.n_steps, self.input_dim))
        return super().train_on_batch(x, y)

    def predict(self, sample):
        sample = np.array(sample).reshape((1, -1, self.n_steps, self.input_dim))
        return super().predict(sample)
