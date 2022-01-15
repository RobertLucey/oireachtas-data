import json
import os
import pickle
import datetime

from oireachtas_data.constants import OIREACHTAS_DIR
from oireachtas_data.models.debate import Debate
from oireachtas_data.models.para import Para


def merge_paras(paras):
    '''
    When you don't care about context it's often easier to treat many
    paragraphs as one.

    :param paras:
    :return: A Para object that just merges all the paras you give it into one.
    '''
    return Para(content='\n\n'.join([m.content for m in paras]))


def get_file_content(filepath):
    """
    Read a file regardless of the extension

    For instance if there's some pickle files and some pickle.bz files
    this will give back the same data as if they were not compressed

    :param filepath: Filepath to read from
    :return: Depending on the ext it may be a pickled obj / str
    """
    ext = os.path.splitext(filepath)[1]
    if ext == '.txt':
        return open(filepath, 'r').read()
    elif ext == '.json':
        f = open(filepath, 'r')
        data = json.loads(f.read())
        f.close()
        return data
    elif ext == '.pickle':
        return pickle.load(open(filepath, 'rb'))
    else:
        raise NotImplementedError()


def get_debates():
    debates = []
    for f in os.listdir(OIREACHTAS_DIR):
        if f.endswith('.json'):
            debates.append(
                Debate.from_file(
                    os.path.join(
                        OIREACHTAS_DIR,
                        f
                    )
                )
            )
    return debates
