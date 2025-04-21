from PySide6.QtWidgets import QDockWidget, QPushButton
from PySide6.QtCore import Qt
from PyMITM.mitm_subapplication import AbstractApp
import random

class ExampleApp_Controller(AbstractApp):
    '''
    A class demonstrating a simple app to use with MITM. 
    App controllers should always inherit from AbstractApp.

    Attributes
    ----------
    model : ExampleApp_Model
        container for application logic
    viewer : ExampleApp_Viewer
        container for application GUI

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
    change_appearance(darkMode)
        modify the app's appearance when Dark Mode is toggled
    exit_cleanup()
        perform any necessary cleanup when the user closes MITM
    get_button()
        return a reference to the button
    change_button_color(button)
        change the given button color to a random color
    set_plot_widget(plotWidget)
        change the model's reference to the given plotWidget
    check_coordinates()
        copies the most recent coordinates under the mouse to the button   
    '''

    def __init__(self, id):
        '''
        Constructs necessary attributes for the ExampleApp_Controller object

        Parameters
        -----------
        self : object
            The class instance.
        id : int
            the ID of the app, used to talk to other ExampleApp_Controllers
        '''
        super().__init__()
        self.model = ExampleApp_Model(id)
        self.viewer = ExampleApp_Viewer(self.model.id)
        self.viewer.button.clicked.connect(self.check_coordinates)
        
    # ===== AbstractApp Overrides =====
    # ----- required overrides -----
    def get_name(self):
        '''
        Returns application name. Overrides abstract method in AbstractApp.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -----------
        str 
        '''
        return self.model.name
    
    def get_dock_widget(self):
        '''
        Returns application dock widget. Overrides abstract method in AbstractApp.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -----------
        QDockWidget
                
        '''
        return self.viewer
    
    # ----- optional overrides -----
    def set_mitm_controller(self, controller):
        '''
        Store a reference to MITM Controller.
        Responsible for setting up connections between this app and MITM Controller.
        Overrides method in AbstractApp.

        Parameters
        ----------
        self : object
            The class instance.
        controller : mitm_controller.Controller
            MITM Controller reference

        Returns
        -----------
        None
        
        '''
        super().set_mitm_controller(controller)
        self.mitm_controller.viewer.widget_changed_signal.connect(self.set_plot_widget)
        
    def set_app_dict(self, appdict):
        '''
        Stores a reference to the dictonary of other apps. 
        Responsible for setting up connections between this app and others.
        Overrides method in AbstractApp.

        Parameters
        ----------
        self : object
            The class instance.
        appdict : dict
            dictionary of other apps

        Returns
        -----------
        None
        
        '''
        super().set_app_dict(appdict)

        target_id = self.model.get_target_id()
        self.get_button().clicked.connect(lambda: \
            self.change_button_color(self.app_dict["My Skeleton App " + str(target_id)].get_button()))

    def change_appearance(self, darkMode):
        '''
        Modify the app's appearance when Dark Mode is toggled

        Parameters
        ----------
        self : object
            The class instance.
        darkMode : bool
            whether the current mode is Dark Mode or not

        Returns
        -----------
        None
        
        '''
        color = self.viewer.button.palette().button().color()
        if(darkMode):
            newcolor =self.model.shade_color(color.name(), -60)
        else:
            newcolor =self.model.shade_color(color.name(), 150)
        self.viewer.set_button_color(self.viewer.button, newcolor)
        return super().change_appearance(darkMode)
    
    def exit_cleanup(self):
        '''
        Perform any necessary cleanup when the user closes MITM

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -----------
        None
        
        '''
        print("cleaning up " + self.model.name)
        return super().exit_cleanup()
    
    # ===== App-specific Functions =====
    def get_button(self):
        '''
        Return a reference to the GUI's central button

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -----------
        QPushButton
        '''
        return self.viewer.button

    def change_button_color(self, button):
        '''
        Changes color of the given button to a random color

        Parameters
        ----------
        self : object
            The class instance.
        button : QPushButton
            the button to change the color of

        Returns
        -----------
        None
        '''
        color = self.model.random_color()
        self.viewer.set_button_color(button, color)
    
    def set_plot_widget(self, plotWidget):
        '''
        Changes the model's reference to the given plotWidget

        Parameters
        ----------
        self : object
            The class instance.
        plotWidget : PlotWidgetDock
            the plot widget object to set a reference to

        Returns
        -------
        None
        '''
        self.model.plotWidget = plotWidget

    def check_coordinates(self):
        '''
        Copies the most recent coordinates under the mouse to the button

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
        '''
        if(self.model.plotWidget):
            if(self.model.plotWidget.coordinatesButton.text()):
                self.viewer.button.setText(self.model.plotWidget.coordinatesButton.text())
           

class ExampleApp_Viewer(QDockWidget):
    '''
    The Viewer class for ExampleApp. Should typically inherit from QDockWidget.

    Attributes
    ----------
    button : QPushButton
        Main button for ExampleApp

    Methods
    -------
    set_button_color(button, color)
        change the given button color to the given color
    
    '''

    def __init__(self, id, parent=None):
        '''
        Constructs necessary attributes for the ExampleApp_Viewer object

        Parameters
        -----------
        self : object
            The class instance.
        '''
        QDockWidget.__init__(self, parent)
        self.button = QPushButton("Button " + str(id))
        self.setWidget(self.button)
        self.setAllowedAreas(Qt.AllDockWidgetAreas)

    def set_button_color(self, button, color):
        '''
        Sets color of the given button to the given color

        Parameters
        ----------
        self : object
            The class instance.
        button : QPushButton
            the button to change the color of
        color : QColor
            the color to set the button to

        Returns
        -----------
        None
        '''
        button.setStyleSheet("background-color: " + color + ";")
    
class ExampleApp_Model():
    '''
    The Model class for ExampleApp

    Attributes
    ----------
    id : int
        application id to separate it from other ExampleApps
    name : str
        name of application, combined with ID to make distinct from other ExampleApps
    plotWidget : PlotWidgetDock
        reference to MITM's currently selected PlotWidgetDock object

    Methods
    -------
    get_target_id(id)
        determine ID of ExampleApp whose button will be changed
    random_color()
        generate a random RGB value
    shade_color(color, percent)
        darkens or lightens color by given percent
    
    '''

    def __init__(self, id):
        '''
        Constructs necessary attributes for the ExampleApp_Viewer object

        Parameters
        -----------
        self : object
            The class instance.
        id : int 
            application id to separate it from other ExampleApps
        '''
        self.id = id
        self.name = "My Skeleton App " + str(id)
        self.plotWidget = None

    def get_target_id(self):
        '''
        Determines ID of ExampleApp whose button will be changed

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -----------
        int
        '''
        return (self.id + 1) % 3 + 1
    
    def random_color(self):
        '''
        Generates random RGB color

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -----------
        str
        '''
        return '#' + ''.join(random.choice('0123456789abcdef') for _ in range(6))
    
    def shade_color(self, color, percent) :
        '''
        Darkens or lightens color by given percent
        A positive percent indicates the amount to lighten by
        A negative percent indicates the amount to darken by

        Parameters
        ----------
        self : object
            The class instance.
        color : str
            the color to lighten or darken
        percent : int
            the amount by which to darken or lighten the color

        Returns
        -----------
        str
        '''

        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)

        r = int(r * (100 + percent) / 100)
        g = int(g * (100 + percent) / 100)
        b = int(b * (100 + percent) / 100)

        r = r if (r<255) else 255
        g = g if (g<255) else 255
        b = b if (b<255) else 255 
        
        rr = '0' + str(hex(r))[2:] if len(str(hex(r))[2:]) == 1 else str(hex(r))[2:]
        gg = '0' + str(hex(g))[2:] if len(str(hex(g))[2:]) == 1 else str(hex(g))[2:]
        bb = '0' + str(hex(b))[2:] if len(str(hex(b))[2:]) == 1 else str(hex(b))[2:]

        return "#"+rr+gg+bb


###############################################################################################
import sys

from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtWidgets import QApplication
from PyMITM.mitm_wrapper import Wrapper_Controller
from exampleapp import ExampleApp_Controller

if __name__ == "__main__":
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)

    controller = Wrapper_Controller([ExampleApp_Controller(1), ExampleApp_Controller(2), ExampleApp_Controller(3)])
    window = controller.viewer
    window.show()

    result = app.exec()
    sys.exit(result)

