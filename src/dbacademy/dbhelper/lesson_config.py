__all__ = ["LessonConfig"]

from typing import Optional, Dict, Any
from dbacademy.dbhelper import dbh_constants
from dbacademy.dbhelper.course_config import CourseConfig


class LessonConfig:
    def __init__(self, *,
                 name: Optional[str],
                 create_schema: bool,
                 create_catalog: bool,
                 requires_uc: bool,
                 install_datasets: bool,
                 enable_streaming_support: bool,
                 enable_ml_support: bool,
                 mocks: Optional[Dict[str, Any]] = None):
        """
        The LessonConfig encapsulates those parameters that may change from one lesson to another compared to the CourseConfig which
        encapsulates parameters that should never change for the entire duration of a course.

        This object is mutable until DBAcademyHelper.init() is called at which time mutations are prohibited. This behavior aims to
        avoid situations where parameters are changed but not reflected in the DBAcademyHelper instance
        :param name: See the property by the same name
        :param create_schema: See the property by the same name
        :param create_catalog: See the property by the same name
        :param requires_uc: See the property by the same name
        :param install_datasets: See the property by the same name
        :param enable_streaming_support: See the property by the same name
        :param enable_ml_support: See the property by the same name
        :param mocks: Used for testing, allows for mocking out the parameters __username, __initial_schema and __initial_catalog
        """
        from dbacademy import dbgems
        from dbacademy.common import validate

        self.__course_config = None

        # This pattern might look odd, but the self.__xyz = None creates the class property and then self.xyz is
        # setting the actual value through the provided setter method.

        self.__name = None
        self.__clean_name = None  # Use "setter" to initialize
        self.name = validate(name=name).optional.str()

        self.__installing_datasets = None  # the terms are slightly different for readability
        self.installing_datasets = validate(install_datasets=install_datasets).required.bool()

        self.__requires_uc = None  # Use "setter" to initialize
        self.requires_uc = validate(requires_uc=requires_uc).required.bool()

        self.__enable_streaming_support = None  # Use "setter" to initialize
        self.enable_streaming_support = validate(enable_streaming_support=enable_streaming_support).required.bool()

        self.__enable_ml_support = None  # Use "setter" to initialize
        self.enable_ml_support = validate(enable_ml_support=enable_ml_support).required.bool()

        self.__create_schema = None  # Use "setter" to initialize
        self.create_schema = validate(create_schema=create_schema).required.bool()

        self.__create_catalog = None  # Use "setter" to initialize
        self.create_catalog = validate(create_catalog=create_catalog).required.bool()

        try:
            # Load all three values with a single query
            row = dbgems.sql("SELECT current_user() as username, current_catalog() as catalog, current_database() as schema").first()
            self.__username = row["username"]
            self.__initial_schema = row["schema"]
            self.__initial_catalog = row["catalog"]
        except Exception:
            # Presumably because of unit tests
            self.__username = None
            self.__initial_schema = None
            self.__initial_catalog = None

        # Mock out the following attributes if specified.
        mocks = validate(mocks=mocks).optional.dict(str, auto_create=True)

        self.__username = mocks.get("__username", self.__username)
        self.__initial_schema = mocks.get("__initial_schema", self.__initial_schema)
        self.__initial_catalog = mocks.get("__initial_catalog", self.__initial_catalog)

    def assert_valid(self) -> None:
        if self.create_catalog and not self.is_uc_enabled_workspace:
            raise AssertionError(f"Cannot create a catalog, UC is not enabled for this workspace/cluster.")

        if self.create_catalog and self.create_schema:
            raise AssertionError(f"Cannot create a user-specific schema when creating UC catalogs")

    def lock_mutations(self, course_config: CourseConfig) -> None:
        """
        Called by DBAcademy.init() to lock this object from future mutations.
        :return: None
        """
        self.__course_config = course_config

    def __assert_mutable(self) -> None:
        assert self.__course_config is None, f"LessonConfig is no longer mutable; DBAcademyHelper has already been initialized."

    @property
    def course_config(self) -> Optional[CourseConfig]:
        """The course that this lesson belongs too. This value is initially null and is set by DBAcademyHelper once initialized."""
        return self.__course_config

    @property
    def installing_datasets(self) -> bool:
        """Indicates that the DBAcademyHelper object should install datasets upon invoking DBAcademyHelper.init()"""
        return self.__installing_datasets

    @installing_datasets.setter
    def installing_datasets(self, installing_datasets: bool) -> None:
        if not self.__installing_datasets == installing_datasets:
            self.__assert_mutable()
            self.__installing_datasets = installing_datasets

    @property
    def name(self) -> Optional[str]:
        """
        In most cases the name of a lesson is set to None. In instances where the application state (e.g. databases, working directories, etc.)
        need to be kept from one notebook to the next, specifying the lesson's name ensures that assets like the database name remains
        the same between multiple notebooks.

        When running under test, see DBAcademyHelper.is_smoke_test, a random lesson name will be applied to each lesson, unless one is specifically
        specified, so that testing can run asynchronously without resource contentions between, for example, two lessons attempting to modify
        the same database.

        See also DBAcademyHelper.schema_name & DBAcademyHelper.catalog_name

        :return: The name of the lesson.
        """
        return self.__name

    @name.setter
    def name(self, name: Optional[str]) -> None:
        if not self.__name == name:
            self.__assert_mutable()
            self.__name = name
            self.__clean_name = self.to_clean_lesson_name(name)

    @staticmethod
    def to_clean_lesson_name(name: Optional[str]) -> Optional[str]:
        """
        Utility function to create a "clean" lesson name.

        See also LessonConfig.name
        :param name: the name of the lesson
        :return: the "clean" version of the specified lesson's name
        """
        import re

        if name is None:
            return None

        value = re.sub(r"[^a-zA-Z\d]", "_", str(name))
        while "__" in value:
            value = value.replace("__", "_")
        return value

    @property
    def clean_name(self) -> str:
        """
        A "clean" version of LessonConfig.name wherein all non-alpha characters and non-digits replaced with an underscore.
        :return: the "clean" version of teh lesson's name
        """
        return self.__clean_name

    @property
    def enable_streaming_support(self) -> bool:
        """
        A flag that indicates if support for structure streaming should be provided. The primary usage is to declare a single
        checkpoint super-directory that all steaming checkpoints can be located in for the sake of consistency.
        :return: True if DBAcademyHelper should add support for streaming lessons.
        """
        return self.__enable_streaming_support

    @enable_streaming_support.setter
    def enable_streaming_support(self, enable_streaming_support) -> None:
        if not self.__enable_streaming_support == enable_streaming_support:
            self.__assert_mutable()
            self.__enable_streaming_support = enable_streaming_support

    @property
    def enable_ml_support(self) -> bool:
        """
        A flag that indicates if support for managing ML & MLflow artifacts. The primary usage is to
        purge Feature Tables, Experiments (mainly those created under test), ML Models and Serving Endpoints
        """
        return self.__enable_ml_support

    @enable_ml_support.setter
    def enable_ml_support(self, enable_ml_support) -> None:
        if not self.__enable_ml_support == enable_ml_support:
            self.__assert_mutable()
            self.__enable_ml_support = enable_ml_support

    @property
    def requires_uc(self) -> bool:
        """
        A flag that indicates if the lesson requires support for Unity Catalog. When set to True and when LessonConfig.is_uc_enabled_workspace is False,
        an exception with be throwing with additional instructions on the nature of the error and ultimately directions to remedy the problem.
        :return: True if the lesson requires Unity Catalog
        """
        return self.__requires_uc

    @requires_uc.setter
    def requires_uc(self, requires_uc) -> None:
        if not self.__requires_uc == requires_uc:
            self.__assert_mutable()
            self.__requires_uc = requires_uc

    @property
    def is_uc_enabled_workspace(self) -> bool:
        """
        Returns True if the current workspace is Unity Catalog (UC) enabled and False if not. Absent a more "stable" flag, the
        implementation actually returns True if the catalog is anything other than "spark_catalog", the name
        default catalog name for non-UC environments.
        :return: True if this is a UC environment
        """
        # Implementation here might be a bit odd, but the idea here is that if our
        # initial catalog was "spark_catalog" then it's not UC. If the catalog is
        # "hive_metastore" then we know it is UC, but that is also true if the catalog
        # was "mickey_mouse_house". That leads to the conclusion that it's UC
        # if it's anything other than "spark_catalog"

        initial_catalog = self.initial_catalog
        if initial_catalog is None:
            return False  # If not set then not UC
        elif initial_catalog == dbh_constants.DBACADEMY_HELPER.CATALOG_SPARK_DEFAULT:
            return False  # If is "spark_catalog", then not UC
        else:
            return True  # In all other cases, assumed to be UC.

    @property
    def initial_catalog(self) -> str:
        """
        :return: the name of the catalog at the moment LessonConfig was instantiated.
        """
        return self.__initial_catalog

    @property
    def initial_schema(self) -> str:
        """
        :return: the name of the schema at the moment LessonConfig was instantiated.
        """
        return self.__initial_schema

    @property
    def username(self) -> str:
        """
        :return: the current user's name as determined by invoking "SELECT current_user()" in the consumer's workspace.
        """
        return to_clean_lesson_name(self.__username)

    @property
    def create_catalog(self) -> bool:
        """
        :return: A flag indicating if DBAcademyHelper should create a user-specific catalog upon invocation of DBAcademyHelper.init()
        """
        return self.__create_catalog

    @create_catalog.setter
    def create_catalog(self, create_catalog: bool) -> None:
        if not self.__create_catalog == create_catalog:
            self.__assert_mutable()
            self.__create_catalog = create_catalog

    @property
    def create_schema(self) -> bool:
        """
        :return: A flag indicating if DBAcademyHelper should create a user-specific schema upon invocation of DBAcademyHelper.init()
        """
        return self.__create_schema

    @create_schema.setter
    def create_schema(self, create_schema: bool) -> None:
        if not self.__create_schema == create_schema:
            self.__assert_mutable()
            self.__create_schema = create_schema
