import pandas as pd
import numpy as np


class Item(object):
    """

    """

    def __init__(self, size, id_start=0):
        """

        :param size:
        :param id_start:
        :return:
        """
        ids = np.arange(id_start, id_start + size)
        self._table = pd.DataFrame(index = ids)

    def add_attribute(self, name, generator):
        """Adds a column named "name" to the inner table of the item, randomly generated from the generator.

        :param name: string, will be used as name for the column in the table
        :param generator: class from the random_generator series. needs to have a generate function that works
        :return: none
        """
        self._table[name] = generator.generate(len(self._table.index))

    def check_condition(self,ids,f,param):
        raise Exception("Not yet supported")

    def __repr__(self):
        return self._table


class CellItem(Item):
    def __init__(self, size, id_start, status_gen):
        """

        :param size:
        :param id_start:
        :param status_gen:
        :return:
        """
        Item.__init__(self,size,id_start)
        self.add_attribute("STATUS", status_gen)

    def is_on(self,ids):
        """

        :param ids:
        :return:
        """
        return self._table.loc[ids,"STATUS"] == 1

    def update_status(self):
        pass