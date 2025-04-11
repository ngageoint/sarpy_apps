# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'rcs_tool.ui'
##
## Created by: Qt User Interface Compiler version 6.8.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QLocale,
    QMetaObject,
    QObject,
    QPoint,
    QRect,
    QSize,
    QTime,
    QUrl,
    Qt,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QGradient,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QCheckBox,
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from . import rcs_viewer


class Ui_RCSTool(object):
    def setupUi(self, RCSTool):
        if not RCSTool.objectName():
            RCSTool.setObjectName("RCSTool")
        RCSTool.resize(1275, 327)
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName("dockWidgetContents")
        self.verticalLayout_2 = QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.dock_widget_contents = QHBoxLayout()
        self.dock_widget_contents.setObjectName("dock_widget_contents")
        self.dock_widget_contents.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.rcs_roi_view = QVBoxLayout()
        self.rcs_roi_view.setObjectName("rcs_roi_view")

        self.dock_widget_contents.addLayout(self.rcs_roi_view)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QLabel(self.dockWidgetContents)
        self.label.setObjectName("label")
        self.label.setScaledContents(True)
        self.label.setAlignment(Qt.AlignCenter)

        self.verticalLayout.addWidget(self.label)

        self.rcs_measure_units_combo_box = QComboBox(self.dockWidgetContents)
        self.rcs_measure_units_combo_box.addItem("")
        self.rcs_measure_units_combo_box.addItem("")
        self.rcs_measure_units_combo_box.addItem("")
        self.rcs_measure_units_combo_box.addItem("")
        self.rcs_measure_units_combo_box.addItem("")
        self.rcs_measure_units_combo_box.setObjectName("rcs_measure_units_combo_box")

        self.verticalLayout.addWidget(self.rcs_measure_units_combo_box)

        self.rcs_geometry_table = rcs_viewer.GeometryTableWidget(
            self.dockWidgetContents
        )
        self.rcs_geometry_table.setObjectName("rcs_geometry_table")

        self.verticalLayout.addWidget(self.rcs_geometry_table)

        self.label_2 = QLabel(self.dockWidgetContents)
        self.label_2.setObjectName("label_2")
        self.label_2.setScaledContents(True)
        self.label_2.setAlignment(Qt.AlignCenter)

        self.verticalLayout.addWidget(self.label_2)

        self.rcs_slow_time_units_combo_box = QComboBox(self.dockWidgetContents)
        self.rcs_slow_time_units_combo_box.addItem("")
        self.rcs_slow_time_units_combo_box.addItem("")
        self.rcs_slow_time_units_combo_box.addItem("")
        self.rcs_slow_time_units_combo_box.addItem("")
        self.rcs_slow_time_units_combo_box.addItem("")
        self.rcs_slow_time_units_combo_box.setObjectName(
            "rcs_slow_time_units_combo_box"
        )

        self.verticalLayout.addWidget(self.rcs_slow_time_units_combo_box)

        self.verticalLayout.setStretch(0, 5)
        self.verticalLayout.setStretch(1, 5)
        self.verticalLayout.setStretch(2, 80)
        self.verticalLayout.setStretch(3, 5)
        self.verticalLayout.setStretch(4, 5)

        self.dock_widget_contents.addLayout(self.verticalLayout)

        self.rcs_data_layout = QVBoxLayout()
        self.rcs_data_layout.setObjectName("rcs_data_layout")
        self.tabWidget_2 = QTabWidget(self.dockWidgetContents)
        self.tabWidget_2.setObjectName("tabWidget_2")
        self.tab_1 = QWidget()
        self.tab_1.setObjectName("tab_1")
        self.horizontalLayout_2 = QHBoxLayout(self.tab_1)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.rcs_table_view = rcs_viewer.RCSTableWidget(self.tab_1)
        if self.rcs_table_view.columnCount() < 6:
            self.rcs_table_view.setColumnCount(6)
        __qtablewidgetitem = QTableWidgetItem()
        self.rcs_table_view.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.rcs_table_view.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.rcs_table_view.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.rcs_table_view.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.rcs_table_view.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.rcs_table_view.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        if self.rcs_table_view.rowCount() < 5:
            self.rcs_table_view.setRowCount(5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.rcs_table_view.setVerticalHeaderItem(0, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.rcs_table_view.setVerticalHeaderItem(1, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.rcs_table_view.setVerticalHeaderItem(2, __qtablewidgetitem8)
        __qtablewidgetitem9 = QTableWidgetItem()
        self.rcs_table_view.setVerticalHeaderItem(3, __qtablewidgetitem9)
        __qtablewidgetitem10 = QTableWidgetItem()
        self.rcs_table_view.setVerticalHeaderItem(4, __qtablewidgetitem10)
        self.rcs_table_view.setObjectName("rcs_table_view")
        self.rcs_table_view.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

        self.horizontalLayout_2.addWidget(self.rcs_table_view)

        self.tabWidget_2.addTab(self.tab_1, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName("tab_2")
        self.horizontalLayout_3 = QHBoxLayout(self.tab_2)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.rcs_slow_plot_view = QVBoxLayout()
        self.rcs_slow_plot_view.setObjectName("rcs_slow_plot_view")

        self.horizontalLayout_3.addLayout(self.rcs_slow_plot_view)

        self.tabWidget_2.addTab(self.tab_2, "")
        self.tab_3 = QWidget()
        self.tab_3.setObjectName("tab_3")
        self.horizontalLayout = QHBoxLayout(self.tab_3)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.rcs_fast_plot_view = QVBoxLayout()
        self.rcs_fast_plot_view.setObjectName("rcs_fast_plot_view")

        self.horizontalLayout.addLayout(self.rcs_fast_plot_view)

        self.tabWidget_2.addTab(self.tab_3, "")

        self.rcs_data_layout.addWidget(self.tabWidget_2)

        self.dock_widget_contents.addLayout(self.rcs_data_layout)

        self.rcs_button_layout = QVBoxLayout()
        self.rcs_button_layout.setObjectName("rcs_button_layout")
        self.rcs_add_geometry_button = QPushButton(self.dockWidgetContents)
        self.rcs_add_geometry_button.setObjectName("rcs_add_geometry_button")

        self.rcs_button_layout.addWidget(self.rcs_add_geometry_button)

        self.rcs_import_button = QPushButton(self.dockWidgetContents)
        self.rcs_import_button.setObjectName("rcs_import_button")

        self.rcs_button_layout.addWidget(self.rcs_import_button)

        self.rcs_export_button = QPushButton(self.dockWidgetContents)
        self.rcs_export_button.setObjectName("rcs_export_button")

        self.rcs_button_layout.addWidget(self.rcs_export_button)

        self.rcs_toggle_voids_button = QCheckBox(self.dockWidgetContents)
        self.rcs_toggle_voids_button.setObjectName("rcs_toggle_voids_button")

        self.rcs_button_layout.addWidget(self.rcs_toggle_voids_button)

        self.dock_widget_contents.addLayout(self.rcs_button_layout)

        self.dock_widget_contents.setStretch(0, 30)
        self.dock_widget_contents.setStretch(1, 10)
        self.dock_widget_contents.setStretch(2, 50)
        self.dock_widget_contents.setStretch(3, 10)

        self.verticalLayout_2.addLayout(self.dock_widget_contents)

        RCSTool.setWidget(self.dockWidgetContents)

        self.retranslateUi(RCSTool)

        self.tabWidget_2.setCurrentIndex(0)

        QMetaObject.connectSlotsByName(RCSTool)

    # setupUi

    def retranslateUi(self, RCSTool):
        RCSTool.setWindowTitle(QCoreApplication.translate("RCSTool", "RCS Tool", None))
        self.label.setText(QCoreApplication.translate("RCSTool", "Measure", None))
        self.rcs_measure_units_combo_box.setItemText(
            0, QCoreApplication.translate("RCSTool", "RCS", None)
        )
        self.rcs_measure_units_combo_box.setItemText(
            1, QCoreApplication.translate("RCSTool", "Pixel Power", None)
        )
        self.rcs_measure_units_combo_box.setItemText(
            2, QCoreApplication.translate("RCSTool", "Beta Zero", None)
        )
        self.rcs_measure_units_combo_box.setItemText(
            3, QCoreApplication.translate("RCSTool", "Gamma Zero", None)
        )
        self.rcs_measure_units_combo_box.setItemText(
            4, QCoreApplication.translate("RCSTool", "Sigma Zero", None)
        )

        self.label_2.setText(
            QCoreApplication.translate("RCSTool", "Slow Time Units", None)
        )
        self.rcs_slow_time_units_combo_box.setItemText(
            0, QCoreApplication.translate("RCSTool", "Collect Time", None)
        )
        self.rcs_slow_time_units_combo_box.setItemText(
            1, QCoreApplication.translate("RCSTool", "Polar Angle", None)
        )
        self.rcs_slow_time_units_combo_box.setItemText(
            2, QCoreApplication.translate("RCSTool", "Azimuth Angle", None)
        )
        self.rcs_slow_time_units_combo_box.setItemText(
            3, QCoreApplication.translate("RCSTool", "Aperture Relative", None)
        )
        self.rcs_slow_time_units_combo_box.setItemText(
            4, QCoreApplication.translate("RCSTool", "Target Relative", None)
        )

        ___qtablewidgetitem = self.rcs_table_view.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(
            QCoreApplication.translate("RCSTool", "Polarization", None)
        )
        ___qtablewidgetitem1 = self.rcs_table_view.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(
            QCoreApplication.translate("RCSTool", "Mean Power [dB]", None)
        )
        ___qtablewidgetitem2 = self.rcs_table_view.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(
            QCoreApplication.translate("RCSTool", "Mean Power", None)
        )
        ___qtablewidgetitem3 = self.rcs_table_view.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(
            QCoreApplication.translate("RCSTool", "STD Power", None)
        )
        ___qtablewidgetitem4 = self.rcs_table_view.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(
            QCoreApplication.translate("RCSTool", "Min Power", None)
        )
        ___qtablewidgetitem5 = self.rcs_table_view.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(
            QCoreApplication.translate("RCSTool", "Max Power", None)
        )
        ___qtablewidgetitem6 = self.rcs_table_view.verticalHeaderItem(0)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("RCSTool", "RCS", None))
        ___qtablewidgetitem7 = self.rcs_table_view.verticalHeaderItem(1)
        ___qtablewidgetitem7.setText(
            QCoreApplication.translate("RCSTool", "Pixel Power", None)
        )
        ___qtablewidgetitem8 = self.rcs_table_view.verticalHeaderItem(2)
        ___qtablewidgetitem8.setText(
            QCoreApplication.translate("RCSTool", "Beta Zero", None)
        )
        ___qtablewidgetitem9 = self.rcs_table_view.verticalHeaderItem(3)
        ___qtablewidgetitem9.setText(
            QCoreApplication.translate("RCSTool", "Gamma Zero", None)
        )
        ___qtablewidgetitem10 = self.rcs_table_view.verticalHeaderItem(4)
        ___qtablewidgetitem10.setText(
            QCoreApplication.translate("RCSTool", "Sigma Zero", None)
        )
        self.tabWidget_2.setTabText(
            self.tabWidget_2.indexOf(self.tab_1),
            QCoreApplication.translate("RCSTool", "RCS Table", None),
        )
        self.tabWidget_2.setTabText(
            self.tabWidget_2.indexOf(self.tab_2),
            QCoreApplication.translate("RCSTool", "Slow Time Response", None),
        )
        self.tabWidget_2.setTabText(
            self.tabWidget_2.indexOf(self.tab_3),
            QCoreApplication.translate("RCSTool", "Fast Time Response", None),
        )
        self.rcs_add_geometry_button.setText(
            QCoreApplication.translate("RCSTool", "Add Geometry", None)
        )
        self.rcs_import_button.setText(
            QCoreApplication.translate("RCSTool", "Import", None)
        )
        self.rcs_export_button.setText(
            QCoreApplication.translate("RCSTool", "Export", None)
        )
        self.rcs_toggle_voids_button.setText(
            QCoreApplication.translate("RCSTool", "Include Voids", None)
        )

    # retranslateUi
