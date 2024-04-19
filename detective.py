from os.path import isdir, exists, getctime, isfile
from os import walk, name as os_name, getcwd
import os
from getpass import getuser
from datetime import datetime
from configparser import ConfigParser
import re

class Detective():
    """
    Осуществляет поиск файлов имя которых соответствует регулярному выражению. По умолчанию поиск 
    производится в директории Downloads(Загрузки) и текущей рабочей директории.

    Поддерживаются Linux, Windows и MacOS  
    """
    _title_section = 'Пути'
    _name_downls_op = 'Загрузки'
    _nm_addtn_op = 'Дополнительные директории'

    def __init__( self, regex:str, config_file:str, **kwarg) -> None:
        """
        Получает регулярное выражение
        на соответствие с которым будут проверяться имена файлов, а также
        полное имя(с путем) файла конфигурации, в котором будет сохранятся директории
        для поиска
        
        Если файл конфигурации не был найден, то создает новый и сохраняет в нем путь до папки Downloads(Загрузки)

        Дополнительные параметры:
        - sep - разделитель в списке дополнительных директорий в файле конфигурации. По умолчанию разделителем является символ переноса на новую строку
        - encoding - кодировка. По умолчанию UTF-8
        """
        self._regex = regex
        self._config_file = config_file
        self._files = {}

        self._separator = str( kwarg.get( 'sep', '\n' ) )
        self._encoding = kwarg.get( 'encoding', 'UTF-8' )

        if not exists( self._config_file ):
            self._create_config()

        self._downloads = self._get_downloads()
        self._additionals = self._get_additional_dir()

    def _get_from_config( self, name_option:str ) -> str:
        config = ConfigParser()
        config.read( self._config_file, encoding = self._encoding ) 

        return config.get( self._title_section, name_option )

    def _get_downloads( self ) -> str:
        return self._get_from_config( self._name_downls_op )

    def _get_additional_dir( self ) -> list:
        additionals = self._get_from_config( self._nm_addtn_op )

        if additionals:
            return self._exclude_duplicates( additionals.split( self._separator ) )
        
        else:
            return list()
    
    def _exclude_duplicates( self, dirs:list ) -> list:
        #Сначала преобразовывает в словарь, тем самым исключая дубликаты и сохраняя порядок, а затем обратно в список
        return list( dict.fromkeys( dirs ) )
        
    def _find_downloads( self ) -> str:
        if os_name == 'nt':
            #Если ОС Windows, то начинает поиск с директории C:/Users/<имя текущего пользователя>/
            start = "\N{Reverse Solidus}".join( [ 'C:', 'Users', getuser(), ''] )

        else:
            #Если ОС Linux или MacOS, то начинает поиск с директории /home/<имя текущего пользователя>/
            start = "/home/{}/".format( getuser() )

        for root, dirs, files in walk( start ):
            for dir in dirs:
                if dir == 'Downloads' or dir == 'Загрузки':
                    return os.path.join( root, dir )
    
    def _create_config( self ) -> None:
        config = ConfigParser()
        config.add_section( self._title_section )
        config.set( self._title_section, self._name_downls_op, self._find_downloads() )
        config.set( self._title_section, self._nm_addtn_op, '' )
        with open( self._config_file, 'w', encoding = self._encoding ) as config_file:
            config.write( config_file )

    def _save_additional( self ) -> None:
        config = ConfigParser()
        config.read( self._config_file, encoding = self._encoding )

        with open( self._config_file, 'w', encoding = self._encoding ) as config_file:
            config.set( self._title_section, self._nm_addtn_op, self._separator.join( self._additionals ) )
            config.write( config_file )

    def _get_creation_time( self, file_name:str ) -> datetime:
        return datetime.fromtimestamp( getctime( file_name ) )
    
    def _is_correct_path( self, path:str ) -> bool:
        return isdir( path )



    def find_files( self ) -> None:
        """
        Производит рекурсивный обход всех директорий в поисках файлов, имена 
        которых соответствуют регулярному выражению
        
        Порядок обхода директорий:
        Downloads(Загрузки) -> Дополнительные директории -> Текущая рабочая директория
        
        При каждом вызове стирает предыдущий результат
        
        Если ни одного файла не удалось найти, то возбуждается исключение FileNotFoundError 
        """
        self._files.clear()

        for path in self.get_path():
            for root, dirs, files in walk( path ):
                for file in files:
                    if re.fullmatch( self._regex, file ):
                        self._files[ ( root, file ) ] = self._get_creation_time( os.path.join( root, file ) )

        if not self._files:
            raise FileNotFoundError( 'Ни один файл не был найден' )
    
    def get_today_recent_file( self ) -> dict | None:
        """
        Возвращает словарь с данными самого последнего созданного за сегодня файла из найденных, в противном случае - возвращает None

        Словарь содержит следующие ключи: name - имя файла; path - путь до файла; date - дата и время создания файла. Все значения ключей - строки

        Вызывать метод следует после вызова find_files
        """
        if not self._files:
            return None

        recent_file = None

        for file in self._files:
            if not recent_file:
                recent_file = file
                continue

            if self._files[ file ] > self._files[ recent_file ]:
                recent_file = file

        if self._files[ recent_file ].date() == datetime.now().date():
            return { 'name': recent_file[ 1 ],
                    'path': recent_file[ 0 ],
                    'date': self._files[ recent_file ] 
                    }

        return None
    
    def get_path( self ) -> list:
        """
        Возвращается список всех директорий, в которых производится поиск

        Директорие упорядочены следующим образом: Downloads(Загрузки) -> Дополнительные директории -> Текущая рабочая директория
        """
        path = []
        path.append( self._downloads )
        path.extend( self._additionals )
        path.append( getcwd() )

        return path
    
    def add_path( self, path:str ) -> bool:
        """
        Добавляет директорию, в которой будет производится поиск файлов

        Если директории нет в списке, добавляет и возвращает True, в противном случае - ничего не делает и возвращает False

        Если был передан некорректный путь до директории возбуждает исключение NotADirectoryError
        """
        if self._is_correct_path( path ):  
            if not path in self._additionals:
                self._additionals.append( path )
                self._save_additional()
                return True
            else:
                return False
        else:
            raise NotADirectoryError( f'Не является директорией: { path }' )
        
    def get_files( self ) -> dict:
        """
        Возвращает словарь c найденными файлами
        
        Ключом является кортеж из пути до файла и его имени. Значение - объект datatime хранящий дату и время создания файла

        Вызывать метод следует после вызова find_files
        """
        return self._files.copy()