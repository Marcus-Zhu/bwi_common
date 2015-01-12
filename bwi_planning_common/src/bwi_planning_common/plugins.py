#!/bin/env python

from python_qt_binding.QtCore import Qt
from python_qt_binding.QtGui import QFrame, QHBoxLayout, QImage, QLabel, QMessageBox, QPainter, QPushButton, \
                                    QVBoxLayout, QWidget
from qt_gui.plugin import Plugin

from .location_function import LocationFunction
from .door_function import DoorFunction
from .utils import clearLayoutAndFixHeight

class MapImage(QLabel):

    def __init__(self, parent=None):
        super(MapImage, self).__init__(parent)

        # Image
        self.setFixedHeight(480)
        self.setFixedWidth(1080)
        self.setObjectName("map_image")

        # Set defaults to handle mouse events, as if these are not setup and a user clicks on the image, then all future
        # mouse events are ignored.
        self.enableDefaultMouseHooks()

        # Create an image for the original map. This will never change.
        # TODO read map from ROS param.
        map_image_location = "/home/piyushk/rocon/src/bwi_common/utexas_gdc/maps/3ne-real-new.pgm"
        map_image = QImage(map_image_location)
        self.map_image = map_image.scaled(1080, 480, Qt.KeepAspectRatio)

        # Create a pixmap for the overlay. This will be modified by functions to change what is being displayed 
        # on the screen.
        self.overlay_image = QImage(self.map_image.size(), QImage.Format_ARGB32_Premultiplied) 
        self.overlay_image.fill(Qt.transparent)

        self.update()

    def defaultMouseHandler(self, event):
        # Do nothing.
        pass

    def enableDefaultMouseHooks(self):
        self.mousePressEvent = self.defaultMouseHandler
        self.mouseMoveEvent = self.defaultMouseHandler
        self.mouseReleaseEvent = self.defaultMouseHandler

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(event.rect(), self.map_image, event.rect())
        painter.drawImage(event.rect(), self.overlay_image, event.rect())
        painter.end()

class LogicalMarkerPlugin(Plugin):

    def __init__(self, context):
        super(LogicalMarkerPlugin, self).__init__(context)

        # TODO read in map file and data directory.
        # Give QObjects reasonable names
        self.setObjectName('LogicalMarkerPlugin')

        # Create QWidget
        self.master_widget = QWidget()
        self.master_layout = QVBoxLayout(self.master_widget)

        # Main Functions - Doors, Locations, Objects
        self.function_layout = QHBoxLayout()
        self.master_layout.addLayout(self.function_layout)
        self.function_buttons = []
        self.current_function = None
        for button_text in ['Locations', 'Doors']: #, 'Objects']:
            button = QPushButton(button_text, self.master_widget)
            button.clicked[bool].connect(self.handle_function_button)
            button.setCheckable(True)
            self.function_layout.addWidget(button)
            self.function_buttons.append(button)
        self.function_layout.addStretch(1)

        self.master_layout.addWidget(self.get_horizontal_line())

        # Subfunction toolbar
        self.subfunction_layout = QHBoxLayout()
        clearLayoutAndFixHeight(self.subfunction_layout)
        self.master_layout.addLayout(self.subfunction_layout)
        self.current_subfunction = None

        self.master_layout.addWidget(self.get_horizontal_line())

        self.image = MapImage(self.master_widget)
        self.master_layout.addWidget(self.image)

        self.master_layout.addWidget(self.get_horizontal_line())

        # Configuration toolbar
        self.configuration_layout = QHBoxLayout()
        clearLayoutAndFixHeight(self.configuration_layout)
        self.master_layout.addLayout(self.configuration_layout)

        # Add a stretch at the bottom.
        self.master_layout.addStretch(1)

        self.master_widget.setObjectName('LogicalMarkerPluginUI')
        if context.serial_number() > 1:
            self.master_widget.setWindowTitle(self.master_widget.windowTitle() + (' (%d)' % context.serial_number()))
        context.add_widget(self.master_widget)


        # Activate the functions
        self.functions = {}
        self.functions['Locations'] = LocationFunction('/home/piyushk/test.yaml',
                                                       self.master_widget, 
                                                       self.subfunction_layout, 
                                                       self.configuration_layout,
                                                       self.image)
        self.functions['Doors'] = DoorFunction('/home/piyushk/doors.yaml',
                                               self.functions['Locations'],
                                               self.master_widget, 
                                               self.subfunction_layout, 
                                               self.configuration_layout,
                                               self.image)

    def construct_layout(self):
        pass

    def get_horizontal_line(self):
        """
        http://stackoverflow.com/questions/5671354/how-to-programmatically-make-a-horizontal-line-in-qt
        """
        hline = QFrame()
        hline.setFrameShape(QFrame.HLine)
        hline.setFrameShadow(QFrame.Sunken)
        return hline

    def handle_function_button(self):
        source = self.sender()

        if source.text() == self.current_function:
            source.setChecked(True)
            return

        # Depress all other buttons.
        for button in self.function_buttons:
            if button != source:
                button.setChecked(False)

        if self.current_function is not None:
            self.functions[self.current_function].deactivateFunction()
        self.current_function = source.text()

        # Clear all subfunction buttons.
        clearLayoutAndFixHeight(self.subfunction_layout)

        if self.current_function is not None:
            self.functions[self.current_function].activateFunction()

    def shutdown_plugin(self):
        modified = False
        for function in self.functions:
            if self.functions[function].isModified():
                modified = True
        if modified:
            ret = QMessageBox.warning(self.master_widget, "Save",
                        "The logical map has been modified.\n"
                        "Do you want to save your changes?",
                        QMessageBox.Save | QMessageBox.Discard)
            if ret == QMessageBox.Save:
                for function in self.functions:
                    if self.functions[function].isModified():
                        self.functions[function].saveConfiguration()

    def save_settings(self, plugin_settings, instance_settings):
        pass

    def restore_settings(self, plugin_settings, instance_settings):
        pass
