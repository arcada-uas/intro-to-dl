# coding: utf-8

# # 20 Newsgroups text classification with pre-trained word embeddings
#
# In this notebook, we'll use pre-trained [GloVe word
# embeddings](http://nlp.stanford.edu/projects/glove/) for text
# classification using PyTorch. This notebook is largely based on the
# blog post [Using pre-trained word embeddings in a Keras
# model]
# (https://blog.keras.io/using-pre-trained-word-embeddings-in-a-keras-model.html)
# by François Chollet.
#
# **Note that using a GPU with this notebook is highly recommended.**
#
# First, the needed imports.

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.autograd import Variable
from torch.utils.data import TensorDataset, DataLoader

from distutils.version import LooseVersion as LV

from keras.preprocessing import sequence, text

from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix

import os
import sys

import numpy as np

if torch.cuda.is_available():
    device = torch.device('cuda')
else:
    device = torch.device('cpu')

print('Using PyTorch version:', torch.__version__, ' Device:', device)
assert(LV(torch.__version__) >= LV("1.0.0"))

# TensorBoard is a tool for visualizing progress during training.
# Although TensorBoard was created for TensorFlow, it can also be used
# with PyTorch.  It is easiest to use it with the tensorboardX module.

try:
    import tensorboardX
    import os, datetime
    logdir = os.path.join(os.getcwd(), "logs",
                          "20ng-cnn"+datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
    print('TensorBoard log directory:', logdir)
    os.makedirs(logdir)
    log = tensorboardX.SummaryWriter(logdir)
except ImportError as e:
    log = None

# ## GloVe word embeddings
#
# Let's begin by loading a datafile containing pre-trained word
# embeddings.  The datafile contains 100-dimensional embeddings for
# 400,000 English words.

GLOVE_DIR = "/wrk/makoskel/glove.6B"

print('Indexing word vectors.')

embeddings_index = {}
with open(os.path.join(GLOVE_DIR, 'glove.6B.100d.txt')) as f:
    for line in f:
        values = line.split()
        word = values[0]
        coefs = np.asarray(values[1:], dtype='float32')
        embeddings_index[word] = coefs

print('Found %s word vectors.' % len(embeddings_index))

print('Examples of embeddings:')
for w in ['some', 'random', 'words']:
    print(w, embeddings_index[w])


# ## 20 Newsgroups data set
#
# Next we'll load the [20 Newsgroups]
# (http://www.cs.cmu.edu/afs/cs.cmu.edu/project/theo-20/www/data/news20.html)
# data set.
#
# The dataset contains 20000 messages collected from 20 different
# Usenet newsgroups (1000 messages from each group):
#
# | alt.atheism           | soc.religion.christian   | comp.windows.x     | sci.crypt
# | talk.politics.guns    | comp.sys.ibm.pc.hardware | rec.autos          | sci.electronics
# | talk.politics.mideast | comp.graphics            | rec.motorcycles    | sci.space
# | talk.politics.misc    | comp.os.ms-windows.misc  | rec.sport.baseball | sci.med
# | talk.religion.misc    | comp.sys.mac.hardware    | rec.sport.hockey   | misc.forsale

TEXT_DATA_DIR = "/wrk/makoskel/20_newsgroup"

print('Processing text dataset')

texts = []  # list of text samples
labels_index = {}  # dictionary mapping label name to numeric id
labels = []  # list of label ids
for name in sorted(os.listdir(TEXT_DATA_DIR)):
    path = os.path.join(TEXT_DATA_DIR, name)
    if os.path.isdir(path):
        label_id = len(labels_index)
        labels_index[name] = label_id
        for fname in sorted(os.listdir(path)):
            if fname.isdigit():
                fpath = os.path.join(path, fname)
                args = {} if sys.version_info < (3,) else {'encoding': 'latin-1'}
                with open(fpath, **args) as f:
                    t = f.read()
                    i = t.find('\n\n')  # skip header
                    if 0 < i:
                        t = t[i:]
                    texts.append(t)
                labels.append(label_id)

print('Found %s texts.' % len(texts))

# Vectorize the text samples into a 2D integer tensor.

MAX_NUM_WORDS = 10000
MAX_SEQUENCE_LENGTH = 1000

tokenizer = text.Tokenizer(num_words=MAX_NUM_WORDS)
tokenizer.fit_on_texts(texts)
sequences = tokenizer.texts_to_sequences(texts)

word_index = tokenizer.word_index
print('Found %s unique tokens.' % len(word_index))

data = sequence.pad_sequences(sequences, maxlen=MAX_SEQUENCE_LENGTH)

print('Shape of data tensor:', data.shape)
print('Length of label vector:', len(labels))

# Split the data into a training set and a validation set

VALIDATION_SET, TEST_SET = 1000, 4000

x_train, x_test, y_train, y_test = train_test_split(data, labels,
                                                    test_size=TEST_SET,
                                                    shuffle=True,
                                                    random_state=42)

x_train, x_val, y_train, y_val = train_test_split(x_train, y_train,
                                                  test_size=VALIDATION_SET,
                                                  shuffle=False)

print('Shape of training data tensor:', x_train.shape)
print('Length of training label vector:', len(y_train))
print('Shape of validation data tensor:', x_val.shape)
print('Length of validation label vector:', len(y_val))
print('Shape of test data tensor:', x_test.shape)
print('Length of test label vector:', len(y_test))

# Create PyTorch DataLoaders for all data sets:

BATCH_SIZE = 128

print('Train: ', end="")
train_dataset = TensorDataset(torch.LongTensor(x_train),
                              torch.LongTensor(y_train))
train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE,
                          shuffle=True, num_workers=4)
print(len(train_dataset), 'messages')

print('Validation: ', end="")
validation_dataset = TensorDataset(torch.LongTensor(x_val),
                                   torch.LongTensor(y_val))
validation_loader = DataLoader(validation_dataset, batch_size=BATCH_SIZE,
                               shuffle=False, num_workers=4)
print(len(validation_dataset), 'messages')

print('Test: ', end="")
test_dataset = TensorDataset(torch.LongTensor(x_test),
                             torch.LongTensor(y_test))
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE,
                         shuffle=False, num_workers=4)
print(len(test_dataset), 'messages')

# Prepare the embedding matrix:

print('Preparing embedding matrix.')

num_words = min(MAX_NUM_WORDS, len(word_index) + 1)
embedding_dim = 100

embedding_matrix = np.zeros((num_words, embedding_dim))
for word, i in word_index.items():
    if i >= MAX_NUM_WORDS:
        continue
    embedding_vector = embeddings_index.get(word)
    if embedding_vector is not None:
        # words not found in embedding index will be all-zeros.
        embedding_matrix[i] = embedding_vector

embedding_matrix = torch.FloatTensor(embedding_matrix)
print('Shape of embedding matrix:', embedding_matrix.shape)

# ### Initialization

class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.embed = nn.Embedding.from_pretrained(embedding_matrix,
                                                  freeze=True)
        self.conv1 = nn.Conv1d(100, 128, 5)
        self.pool1 = nn.MaxPool1d(5)
        self.conv2 = nn.Conv1d(128, 128, 5)
        self.pool2 = nn.MaxPool1d(5)
        self.conv3 = nn.Conv1d(128, 128, 5)
        self.pool3 = nn.MaxPool1d(35)

        self.fc1 = nn.Linear(128, 128)
        self.fc2 = nn.Linear(128, 20)

    def forward(self, x):
        x = self.embed(x)
        x = x.transpose(1,2)
        x = F.relu(self.conv1(x))
        x = self.pool1(x)
        x = F.relu(self.conv2(x))
        x = self.pool2(x)
        x = F.relu(self.conv3(x))
        x = self.pool3(x)
        x = x.view(-1, 128)
        x = F.relu(self.fc1(x))
        return F.log_softmax(self.fc2(x), dim=1)

model = Net().to(device)
optimizer = optim.RMSprop(model.parameters(), lr=0.005)
criterion = nn.CrossEntropyLoss()

print(model)

# ### Learning

def train(epoch, log_interval=200):
    # Set model to training mode
    model.train()

    # Loop over each batch from the training set
    for batch_idx, (data, target) in enumerate(train_loader):

        # Copy data to GPU if needed
        data = data.to(device)
        target = target.to(device)

        # Zero gradient buffers
        optimizer.zero_grad()

        # Pass data through the network
        output = model(data)

        # Calculate loss
        loss = criterion(output, target)

        # Backpropagate
        loss.backward()

        # Update weights
        optimizer.step()

        if batch_idx % log_interval == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx * len(data), len(train_loader.dataset),
                100. * batch_idx / len(train_loader), loss.data.item()))

def evaluate(loader, loss_vector=None, accuracy_vector=None):
    model.eval()
    loss, correct = 0, 0
    pred_vector = torch.LongTensor()
    pred_vector = pred_vector.to(device)

    for data, target in loader:
        data = data.to(device)
        target = target.to(device)

        output = model(data)

        loss += criterion(output, target).data.item()

        pred = output.data.max(1)[1] # get the index of the max log-probability
        pred_vector = torch.cat((pred_vector, pred))

        correct += pred.eq(target.data).cpu().sum()

    loss /= len(validation_loader)
    if loss_vector is not None:
        loss_vector.append(loss)

    accuracy = 100. * correct.to(torch.float32) / len(loader.dataset)
    if accuracy_vector is not None:
        accuracy_vector.append(accuracy)

    print('Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(
        loss, correct, len(loader.dataset), accuracy))

    return np.array(pred_vector.cpu())


epochs = 20

lossv, accv = [], []
for epoch in range(1, epochs + 1):
    train(epoch)
    with torch.no_grad():
        print('\\nValidation set:')
        evaluate(validation_loader, lossv, accv)

# ### Inference
#
# We evaluate the model using the test set. If accuracy on the test
# set is notably worse than with the training set, the model has
# likely overfitted to the training samples.

with torch.no_grad():
    evaluate(test_loader)
