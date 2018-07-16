import numpy as np
import h5py
import pandas as pd
import time
import logging

from utilities import calculate_scalar, scale


class DataGenerator(object):
    
    def __init__(self, hdf5_path, batch_size, validation_csv, fold_for_validation, seed=1234):
        
        self.random_state = np.random.RandomState(seed)
        self.batch_size = batch_size
        self.fold_for_validation = fold_for_validation

        # Load data
        load_time = time.time()
        
        hf = h5py.File(hdf5_path, 'r')
        self.itemids = np.array([e.decode() for e in hf['itemid'][:]])
        self.x = hf['feature'][:]
        self.y = hf['hasbird'][:][:, np.newaxis]
        self.datasetids = [e.decode() for e in hf['datasetid'][:]]
        hf.close()
        
        logging.info("Load hdf5 time: {} s".format(time.time() - load_time))
        
        
        
        # Calculate scalar
        (self.mean, self.std) = calculate_scalar(self.x)

        # Get training & validation indexes
        (self.train_audio_indexes, self.valid_audio_indexes) = \
            self.get_train_validate_audio_indexes(validation_csv, 
                                                  fold_for_validation)
                                                  
        logging.info("Training audios: {}".format(len(self.train_audio_indexes)))
        logging.info("Validation audios: {}".format(len(self.valid_audio_indexes)))

        
    def get_folds_from_validation_csv(self, validation_csv):
        
        df = pd.read_csv(validation_csv)
        df = pd.DataFrame(df)
        
        _itemids = df['itemid'].tolist()
        _folds = df['fold'].tolist()
        
        folds = []
        
        for itemid in self.itemids:
            
            index = _itemids.index(itemid)
            fold = _folds[index]
            folds.append(fold)
        
        return np.array(folds)
        
        
    def get_train_validate_audio_indexes(self, validation_csv, fold_for_validation):
        """Get indexes of training and validation data. 
        """

        if validation_csv is None:
            train_audio_indexes = np.arange(len(self.y))
            valid_audio_indexes = np.array([])
            
        else:
            audios_num = len(self.y)
            train_audio_indexes = []
            valid_audio_indexes = []
            
            folds = self.get_folds_from_validation_csv(validation_csv)
            
            for n in range(audios_num):
                if folds[n] == fold_for_validation:
                    valid_audio_indexes.append(n)
                else:
                    train_audio_indexes.append(n)
    
            train_audio_indexes = np.array(train_audio_indexes)
            valid_audio_indexes = np.array(valid_audio_indexes)
            
        return train_audio_indexes, valid_audio_indexes
        
    def generate_train(self):
        
        batch_size = self.batch_size
        indexes = np.array(self.train_audio_indexes)
        samples = len(indexes)
        
        self.random_state.shuffle(indexes)
        
        iteration = 0
        pointer = 0
        
        while True:
            
            # Reset pointer
            if pointer >= samples:
                pointer = 0
                self.random_state.shuffle(indexes)
            
            # Get batch indexes
            batch_indexes = indexes[pointer : pointer + batch_size]
            pointer += batch_size
            
            iteration += 1
            
            batch_x = self.x[batch_indexes]
            batch_y = self.y[batch_indexes]
            
            # Transform data
            batch_x = self.transform(batch_x)
            batch_y = batch_y.astype(np.float32)
            
            yield batch_x, batch_y
        
    def generate_validate(self, data_type, max_iteration):
    
        batch_size = self.batch_size
        
        if data_type == 'train':
            indexes = np.array(self.train_audio_indexes)
            
        elif data_type == 'validate':
            indexes = np.array(self.valid_audio_indexes)
            
        else:
            raise Exception("Invalid data_type!")
            
        audios_num = len(indexes)
        
        iteration = 0
        pointer = 0
        
        while True:
            
            if iteration == max_iteration:
                break
            
            if pointer >= audios_num:
                break
            
            # Get batch indexes
            batch_indexes = indexes[pointer : pointer + batch_size]
            pointer += batch_size
            
            iteration += 1
  
            batch_x = self.x[batch_indexes]
            batch_y = self.y[batch_indexes]
            batch_itemids = self.itemids[batch_indexes]
            
            # Transform data
            batch_x = self.transform(batch_x)
            batch_y = batch_y.astype(np.float32)
            
            yield batch_x, batch_y, batch_itemids
            
    def transform(self, x):
        """Transform data. 
        
        Args:
          x: (batch_x, seq_len, freq_bins) | (seq_len, freq_bins)
          
        Returns:
          Transformed data. 
        """

        return scale(x, self.mean, self.std)