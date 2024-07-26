import os
import re
import shutil
import pytr.config

from importlib_resources import files
from yaml import safe_load
from pathlib import Path
from pytr.app_path import DESTINATION_CONFIG_FILE
from pytr.utils import  get_logger


DEFAULT_CONFIG = "default"
UNKNOWN_CONFIG = "unknown"
MULTIPLE_MATCH_CONFIG = "multiple_match"

TEMPLATE_FILE_NAME ="file_destination_config__template.yaml"

# Invalid characters translation table, for cleaning up the variables before using them.
# This was done to avoid issues with for example 'event_subtitle: “Umtausch/Bezug”' which caused a directory which was unintentional.
INVALID_CHARS_TRANSLATION_TABLE = str.maketrans({
    '"': '',
    '?': '',
    '<': '',
    '>': '',
    '*': '',
    '|': '-',
    '/': '-',
    '\\': '-'
})


class DefaultFormateValue(dict):
    def __missing__(self, key):
        return key.join("{}")


class DestinationConfig:
    def __init__(self, config_name: str, filename: str, path: str = None,  pattern: list = None):
        self.config_name = config_name
        self.filename = filename
        self.path = path
        self.pattern = pattern


class Pattern:
    def __init__(self, event_type: str, event_subtitle: str, event_title: str,  section_title: str, document_title: str):
        self.event_type = event_type
        self.event_subtitle = event_subtitle
        self.event_title = event_title
        self.section_title = section_title
        self.document_title = document_title


class FileDestinationProvider:

    def __init__(self):
        '''
        A provider for file path and file names based on the event type and other parameters.
        '''
        self._log = get_logger(__name__)
        
        config_file_path = Path(DESTINATION_CONFIG_FILE)
        if config_file_path.is_file() == False:
            self.__create_default_config(config_file_path)

        config_file = open(config_file_path, "r", encoding="utf8")
        destination_config = safe_load(config_file)

        self.__validate_config(destination_config)

        destinations = destination_config["destination"]
        
        self._destination_configs: list[DestinationConfig] = []

        for config_name in destinations:
            if config_name == DEFAULT_CONFIG:
                self._default_file_config = DestinationConfig(
                    DEFAULT_CONFIG, destinations[DEFAULT_CONFIG]["filename"])
            elif config_name == UNKNOWN_CONFIG:
                self._unknown_file_config = DestinationConfig(
                    UNKNOWN_CONFIG, destinations[UNKNOWN_CONFIG]["filename"], destinations[UNKNOWN_CONFIG]["path"])
            elif config_name == MULTIPLE_MATCH_CONFIG:
                self._multiple_match_file_config  = DestinationConfig(
                    MULTIPLE_MATCH_CONFIG, destinations[MULTIPLE_MATCH_CONFIG]["filename"], destinations[MULTIPLE_MATCH_CONFIG]["path"])
            else:
                patterns = self.__extract_pattern(
                    destinations[config_name].get("pattern", None))
                self._destination_configs.append(DestinationConfig(
                    config_name, destinations[config_name].get("filename", None), destinations[config_name].get("path", None), patterns))

    def get_file_path(self, event_type: str, event_title: str, event_subtitle: str, section_title: str, document_title: str, variables: dict) -> str:
        '''
        Get the file path based on the event type and other parameters.

        Parameters:
        event_type (str): The event type
        event_title (str): The event title
        event_subtitle (str): The event subtitle
        section_title (str): The section title
        document_title (str): The document title
        variables (dict): The variables->value dict to be used in the file path and file name format.
        '''

        matching_configs = self._destination_configs.copy()

        # Maybe this can be improved looks like a lot of code duplication ... on the other hand using a
        # dict for the parameters for example and iterate over it would make it harder to understand
        if event_type is not None:
            matching_configs = list(filter(lambda config: self.__is_matching_config(
                config, "event_type", event_type), matching_configs))
            variables["event_type"] = event_type.translate(INVALID_CHARS_TRANSLATION_TABLE).strip()

        if event_title is not None:
            matching_configs = list(filter(lambda config: self.__is_matching_config(
                config, "event_title", event_title), matching_configs))
            variables["event_title"] = event_title.translate(INVALID_CHARS_TRANSLATION_TABLE).strip()

        if event_subtitle is not None:
            matching_configs = list(filter(lambda config: self.__is_matching_config(
                config, "event_subtitle", event_subtitle), matching_configs))
            variables["event_subtitle"] = event_subtitle.translate(INVALID_CHARS_TRANSLATION_TABLE).strip()

        if section_title is not None:
            matching_configs = list(filter(lambda config: self.__is_matching_config(
                config, "section_title", section_title), matching_configs))
            variables["section_title"] = section_title.translate(INVALID_CHARS_TRANSLATION_TABLE).strip()

        if document_title is not None:
            matching_configs = list(filter(lambda config: self.__is_matching_config(
                config, "document_title", document_title), matching_configs))
            variables["document_title"] = document_title.translate(INVALID_CHARS_TRANSLATION_TABLE).strip()

        if len(matching_configs) == 0:
            self._log.debug(
                f"No destination config found for the given parameters: event_type:{event_type}, event_title:{event_title},event_subtitle:{event_subtitle},section_title:{section_title},document_title:{document_title}")
            return self.__create_file_path(self._unknown_file_config, variables)

        if len(matching_configs) > 1:
            self._log.debug(f"Multiple Destination Patterns where found. Using 'multiple_match' config! Parameter: event_type:{event_type}, event_title:{event_title},event_subtitle:{event_subtitle},section_title:{section_title},document_title:{document_title}")
            return self.__create_file_path(self._multiple_match_file_config, variables)

        return self.__create_file_path(matching_configs[0], variables)

    def __is_matching_config(self, config: DestinationConfig, key: str, value: str):
        for pattern in config.pattern:
            attribute = getattr(pattern, key)
            if attribute is None or re.fullmatch(attribute, value):
                return True

        return False

    def __create_file_path(self, config: DestinationConfig, variables: dict):
        formate_variables = DefaultFormateValue(variables)

        path = config.path
        filename = config.filename
        if filename is None:
            filename = self._default_file_config.filename

        return os.path.join(path, filename).format_map(formate_variables)

    def __extract_pattern(self, pattern_config: list) -> list:
        patterns = []
        for pattern in pattern_config:
            patterns.append(Pattern(pattern.get("event_type", None),
                                    pattern.get("event_subtitle", None),
                                    pattern.get("event_title", None),
                                    pattern.get("section_title", None),
                                    pattern.get("document_title", None)))

        return patterns

    def __validate_config(self, destination_config: dict):
        if "destination" not in destination_config:
            raise ValueError("'destination' key not found in config file")

        destinations = destination_config["destination"]

        # Check if default config is present
        if DEFAULT_CONFIG not in destinations or "filename" not in destinations[DEFAULT_CONFIG]:
            raise ValueError(
                "'default' config not found or filename is not present in 'default' config")

        if UNKNOWN_CONFIG not in destinations or "filename" not in destinations[UNKNOWN_CONFIG] or "path" not in destinations[UNKNOWN_CONFIG]:
            raise ValueError(
                "'unknown' config not found or filename/path is not present in 'unknown' config")

        if MULTIPLE_MATCH_CONFIG not in destinations or "filename" not in destinations[MULTIPLE_MATCH_CONFIG] or "path" not in destinations[MULTIPLE_MATCH_CONFIG]:
            raise ValueError(
                "'multiple_match' config not found or filename/path is not present in 'multiple_match' config")

        for config_name in destinations:
            if config_name != DEFAULT_CONFIG and "path" not in destinations[config_name]:
                raise ValueError(
                    f"'{config_name}' has no path defined in destination config")

    def __create_default_config(self, config_file_path: Path):
        path = files(pytr.config).joinpath(TEMPLATE_FILE_NAME)
        shutil.copyfile(path, config_file_path)
