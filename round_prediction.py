import matplotlib.pyplot as plt
import pandas as pd
import tensorflow as tf

from pandas.api.types import CategoricalDtype

from tensorflow.keras.layers import BatchNormalization, Dense, Dropout, Input
from tensorflow.keras.models import Sequential
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.regularizers import l1, l1_l2, l2

def get_model(dropout=0):
    """
    Returns model to train
    """
    return Sequential([
        Dense(84, activation="relu", input_shape=(42,)),
        Dropout(dropout),
        Dense(84, activation="relu"),
        Dropout(dropout),
        Dense(42, activation="relu"),
        Dropout(dropout),
        Dense(21, activation="relu"),
        Dropout(dropout),
        BatchNormalization(),
        Dense(10, activation="relu"),
        Dropout(dropout),
        Dense(1, activation="sigmoid")
    ])

def split_targets(df):
    """
    Returns target variable as separate vector
    """
    data = df.iloc[:,:-1]
    targets = df.iloc[:,-1]
    return data, targets

def one_hot_encode_data(data):
    """
    One hot encodes categorical columns
    """
    cols = ["map", "ct_team_name", "t_team_name"]
    team_names = ['Natus_Vincere', 'G2', 'Heroic', 'Gambit', 'FURIA',
        'Vitality', 'Virtus.pro', 'NIP', 'Copenhagen_Flames', 'FaZe',
        'Entropiq', 'MOUZ', 'Liquid', 'Astralis', 'ENCE', 'Evil_Geniuses']
    vals = [
        ['Vertigo', 'Overpass', 'Train', 'Nuke', 'Inferno', 'Mirage', 'Dust2', 'Ancient'],
        team_names,
        team_names
    ]
    for c, v in zip(cols, vals):
        data[c] = data[c].astype(CategoricalDtype(v))
        one_hot = pd.get_dummies(data[c], prefix=c)
        data = data.drop(c, axis=1)
        data = data.join(one_hot)
    return data

def main():
    train = pd.read_csv("round_prediction_no_round_type_train.csv")
    test = pd.read_csv("round_prediction_no_round_type_test.csv")

    train_data, train_targets = split_targets(train)
    test_data, test_targets = split_targets(test)

    train_data = one_hot_encode_data(train_data)
    test_data = one_hot_encode_data(test_data)

    model = get_model()
    print(model.summary())

    model.compile(
        optimizer=Adam(),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )

    # Save best model by validation accuracy for evaluation
    # N.B. worse accuracy??
    checkpoint_filepath = '/tmp/checkpoint'
    checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
        filepath=checkpoint_filepath,
        save_weights_only=True,
        monitor='val_accuracy',
        mode='max', 
        save_best_only=True)

    history = model.fit(
        train_data,
        train_targets,
        batch_size=64,
        epochs=500,
        validation_split=0.15,
        callbacks=[tf.keras.callbacks.TensorBoard(), checkpoint_callback],
        verbose=False
    )

    model.load_weights(checkpoint_filepath)
    model.evaluate(
        test_data,
        test_targets,
        verbose=2
    )

    # Plot the training and validation loss
    # plt.plot(history.history['accuracy'])
    # plt.plot(history.history['val_accuracy'])
    # plt.title('Accuracy vs. epochs')
    # plt.ylabel('Accuracy')
    # plt.xlabel('Epoch')
    # plt.legend(['Training', 'Validation'], loc='upper right')
    # plt.show()

    # plt.plot(history.history['loss'])
    # plt.plot(history.history['val_loss'])
    # plt.title('Loss vs. epochs')
    # plt.ylabel('Loss')
    # plt.xlabel('Epoch')
    # plt.legend(['Training', 'Validation'], loc='upper right')
    # plt.show()

if __name__ == "__main__":
    main()