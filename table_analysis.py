import math
import os
from collections import defaultdict
import numpy as np
from typing import List
import pandas as pd
from numpy import ndarray
import pycognaize.document.field
from pycognaize.document import Document
from pycognaize.model import Model as IQModel
from pycognaize.common.numeric_parser import NumericParser
from pycognaize.common.table_utils import assign_indices_to_tables
from loguru import logger


class TableAnalyzer:

    def __init__(self, table_py_name="tables__table", threshold=0.5):
        self.table_values = None
        self.tagged_tables = {}
        self.tables = None
        self.fields_outside_of_tables = {}
        self.table_name = table_py_name
        self.threshold = threshold
        self.document = None

    def get_table_dict(self):
        tables = []
        for table in self.document.x[self.table_name]:
            if not table.tags:
                logger.warning(f"Table has no tags for {self.document.id}")
                continue
            tables.append(table)
        self.tables = assign_indices_to_tables(tables)

    def check_fields(self, document: Document) -> pd.DataFrame:
        """
        Analyzes the fields in the given document and associates them
        with tagged tables if possible.
        Args:
            document (Document): The document to be analyzed.
        Returns:
            dict: A dictionary containing fields that are outside of tables,
                  indexed by Python field name.
                  Each entry contains a list of tuples, where each tuple
                  consists of page number and field value.
        """
        self.document = document
        self.get_table_dict()
        for py_name in self.document.x:
            for field in self.document.x[py_name]:
                if not field.tags:
                    continue
                self.check_field_value_in_table(py_name, field)
        fields_dict = self.fields_outside_of_tables
        df = pd.DataFrame(*fields_dict.values(), index=fields_dict.keys(), columns=['page', 'field_value'])
        df.index.name = 'python_name'
        pd.set_option("display.max_colwidth", None)

        return df

    def check_field_value_in_table(self, py_name: str,
                                   field: pycognaize.document.field):
        """
        Checks if a field's tag matches any of the tagged tables.
        Args:
            py_name (str): The Python field name.
            field (pycognaize.document.field): The field to be checked
                                               for a matching table.
        Returns:
            None
        """
        for idx, table in self.tables.items():
            if IQModel.matches(field.tags[0], table.tags[0],
                               threshold=self.threshold):
                if idx not in self.tagged_tables:
                    self.tagged_tables[idx] = table
                break
        else:
            if py_name in self.fields_outside_of_tables:
                self.fields_outside_of_tables[py_name].append(
                    (field.tags[0].page.page_number, field.value))
            else:
                self.fields_outside_of_tables[py_name] = \
                    [(field.tags[0].page.page_number, field.value)]
            logger.warning(
                f"The field under '{py_name}' python name "
                f"with '{field.value}' value on page"
                f" {field.tags[0].page.page_number} is not in any table")

    def collect_tables_values(self):
        """
        Collects and stores the parsed numeric values from the tagged tables.
        This method iterates through the tagged tables and extracts
        the numeric values from their DataFrame.
        Extracted values are stored in the 'table_values' dictionary,
        indexed by table index.
        Returns:
            None
        """
        self.table_values = {}
        for idx, table in self.tagged_tables.items():
            table_df = table.tags[0].df
            values = self.get_table_values(table_df=table_df)
            if not values:
                logger.warning(f"Couldn't parse any value for table,"
                               f" idx: {idx}")
                continue
            self.table_values[idx] = values

    @staticmethod
    def get_table_values(table_df: pd.DataFrame,
                         ignored_columns: List[int] = None) -> List[float]:
        """
        Extracts numeric values from a table's DataFrame,
         skipping specified ignored columns.
        Args:
            table_df (pd.DataFrame): The DataFrame representing the table.
            ignored_columns (List[int], optional): List of column indices
                                    to be ignored while extracting values.
                                                   Defaults to None.
        Returns:
            List[float]: A list of extracted numeric values from the table.
        """
        if ignored_columns is None:
            ignored_columns = []
        table_values = []
        for row in table_df.values:
            for idx, value in enumerate(row):
                if idx in ignored_columns:
                    continue
                parsed_value = NumericParser(value).parse_numeric()
                if math.isnan(parsed_value):
                    continue
                table_values.append(parsed_value)
        return table_values

    def get_table_results(self) -> pd.DataFrame:
        """
        Calculates the mean and standard deviation of values
        in the tagged tables.
        Returns:
            pd.DataFrame: A DataFrame with rows as mean and standard deviation,
                          and columns as index values.
        """
        self.collect_tables_values()
        results = defaultdict(list)
        for idx, values in self.table_values.items():
            mean = self.calculate_mean(values)
            std = self.calculate_std(values)
            page, table_idx = idx
            results['mean'].append(mean)
            results['std'].append(std)
            results['page number'].append(page)
            results['table index'].append(table_idx)
        df = pd.DataFrame.from_dict(results, orient='columns', )
        pd.set_option("display.max_colwidth", None)

        return df

    @staticmethod
    def calculate_mean(numbers: List[float]) -> ndarray:
        return np.round(np.average(numbers), 2)

    @staticmethod
    def calculate_std(numbers: List[float]) -> ndarray:
        return np.round(np.std(numbers), 2)

