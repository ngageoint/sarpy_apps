from abc import ABCMeta, abstractmethod
from PySide6.QtCore import Qt

class AbstractApp(metaclass=ABCMeta):
    '''
    This class implements the API that MITM uses to communicate with subapps.
    All subapplications must inherit from this class and must override at least
    the first two methods.

    This class is an abstract class and should not be instantiated on its own.

    Attributes
    ----------
    mitm_controller : mitm_controller.Controller
        reference to MITM controller object
    app_dict : dict
        reference to dictionary of sister applications

    Methods
    -------
    get_name()
        returns application name 
    get_dock_widget():
        returns application GUI in the form of a dock widget
    set_mitm_controller(controller)
        store a reference to MITM Controller.
    set_app_dict(appdict)
        store a reference to application dictionary to interface with other apps
    get_preferred_area()
        get the dock area that the app should initially appear in
    change_appearance(darkMode)
        modify the app's appearance when Dark Mode is toggled
    exit_cleanup()
        perform any necessary cleanup when the user closes MITM
        
    '''

    def __init__(self):
        '''
        Constructs necessary attributes for the AbstractApp object.
        Must only ever be called from child class' constructor.

        Parameters
        -----------
        self : object
            The class instance.
        '''
        self.mitm_controller = None
        self.app_dict = None

    @abstractmethod 
    def get_name(self):
        '''
        Abstract method to retrieve app name. 
        Must be overridden in the child class

        Parameters
        -----------
        self : object
            The class instance.

        Returns
        -------
        str
        '''
        pass
    
    @abstractmethod
    def get_dock_widget(self):
        '''
        Abstract method to retrieve app dock widget. 
        Must be overridden in the child class

        Parameters
        -----------
        self : object
            The class instance.

        Returns
        -------
        QDockWidget
        '''
        pass

    def set_mitm_controller(self, controller):
        '''
        Store a reference to MITM Controller.
        Responsible for setting up connections between this app and MITM Controller.
        Overriding is optional.

        Parameters
        -----------
        controller : mitm_controller.Controller
            MITM Controller object

        Returns
        -------
        self : object
            The class instance.
        '''
        self.mitm_controller = controller

    def set_app_dict(self, appdict):
        '''
        Stores a reference to the dictonary of other apps. 
        Responsible for setting up connections between this app and others.
        Overriding is optional.

        Parameters
        -----------
        self : object
            The class instance.
        appdict : dict
            dictionary of sister apps

        Returns
        -------
        None
        '''
        self.app_dict = appdict

    def get_preferred_area(self):
        '''
        Returns the preferred area for the QDockWidget to appear in MITM.
        Overriding is optional.

        Parameters
        -----------
        self : object
            The class instance.

        Returns
        -------
        Qt.DockWidgetAreas
        '''
        return Qt.BottomDockWidgetArea
    
    def change_appearance(self, darkMode):
        '''
        Modify the app's appearance when Dark Mode is toggled
        Overriding is optional.

        Parameters
        -----------
        self : object
            The class instance.
        darkMode : bool
            whether the current mode is Dark Mode or not

        Returns
        -------
        None
        '''
        pass

    def exit_cleanup(self):
        '''
        Perform any necessary cleanup when the user closes MITM
        Overriding is optional.

        Parameters
        -----------
        self : object
            The class instance.

        Returns
        -------
        None
        '''
        pass