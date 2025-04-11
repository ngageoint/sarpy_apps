# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'metaicon_widget.ui'
##
## Created by: Qt User Interface Compiler version 6.8.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QAbstractScrollArea, QApplication, QFrame,
    QHBoxLayout, QHeaderView, QPushButton, QSizePolicy,
    QSpacerItem, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)

from pyqtgraph import PlotWidget

class Ui_MetaIcon(object):
    def setupUi(self, MetaIcon):
        if not MetaIcon.objectName():
            MetaIcon.setObjectName(u"MetaIcon")
        MetaIcon.resize(254, 364)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MetaIcon.sizePolicy().hasHeightForWidth())
        MetaIcon.setSizePolicy(sizePolicy)
        MetaIcon.setStyleSheet(u"QTableWidget {\n"
"	color: #FFFFFF;\n"
"}\n"
"QFrame {\n"
"	border: 0px solid grey;\n"
"}")
        self.verticalLayout = QVBoxLayout(MetaIcon)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(-1, -1, -1, 9)
        self.horizontalFrame = QFrame(MetaIcon)
        self.horizontalFrame.setObjectName(u"horizontalFrame")
        self.horizontalLayout_3 = QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_2)

        self.minimizeButton = QPushButton(self.horizontalFrame)
        self.minimizeButton.setObjectName(u"minimizeButton")

        self.horizontalLayout_3.addWidget(self.minimizeButton)

        self.closeButton = QPushButton(self.horizontalFrame)
        self.closeButton.setObjectName(u"closeButton")

        self.horizontalLayout_3.addWidget(self.closeButton)


        self.verticalLayout.addWidget(self.horizontalFrame)

        self.content_frame = QFrame(MetaIcon)
        self.content_frame.setObjectName(u"content_frame")
        self.content_frame.setStyleSheet(u"background-color: #88000000")
        self.content_frame.setFrameShape(QFrame.StyledPanel)
        self.content_frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.content_frame)
        self.verticalLayout_2.setSpacing(6)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(-1, 9, 9, -1)
        self.upper_table = QTableWidget(self.content_frame)
        if (self.upper_table.columnCount() < 1):
            self.upper_table.setColumnCount(1)
        if (self.upper_table.rowCount() < 4):
            self.upper_table.setRowCount(4)
        __qtablewidgetitem = QTableWidgetItem()
        self.upper_table.setItem(0, 0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.upper_table.setItem(1, 0, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.upper_table.setItem(2, 0, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.upper_table.setItem(3, 0, __qtablewidgetitem3)
        self.upper_table.setObjectName(u"upper_table")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.upper_table.sizePolicy().hasHeightForWidth())
        self.upper_table.setSizePolicy(sizePolicy1)
        self.upper_table.setFocusPolicy(Qt.NoFocus)
        self.upper_table.setStyleSheet(u"background-color: #00000000")
        self.upper_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.upper_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.upper_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.upper_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.upper_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.upper_table.setShowGrid(False)
        self.upper_table.setCornerButtonEnabled(False)
        self.upper_table.setRowCount(4)
        self.upper_table.setColumnCount(1)
        self.upper_table.horizontalHeader().setVisible(False)
        self.upper_table.horizontalHeader().setHighlightSections(False)
        self.upper_table.horizontalHeader().setStretchLastSection(True)
        self.upper_table.verticalHeader().setVisible(False)
        self.upper_table.verticalHeader().setHighlightSections(False)

        self.verticalLayout_2.addWidget(self.upper_table)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.lower_table = QTableWidget(self.content_frame)
        if (self.lower_table.columnCount() < 1):
            self.lower_table.setColumnCount(1)
        if (self.lower_table.rowCount() < 5):
            self.lower_table.setRowCount(5)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.lower_table.setItem(0, 0, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.lower_table.setItem(1, 0, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.lower_table.setItem(2, 0, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.lower_table.setItem(3, 0, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.lower_table.setItem(4, 0, __qtablewidgetitem8)
        self.lower_table.setObjectName(u"lower_table")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.lower_table.sizePolicy().hasHeightForWidth())
        self.lower_table.setSizePolicy(sizePolicy2)
        self.lower_table.setFocusPolicy(Qt.NoFocus)
        self.lower_table.setAutoFillBackground(False)
        self.lower_table.setStyleSheet(u"background-color: #00000000")
        self.lower_table.setFrameShape(QFrame.StyledPanel)
        self.lower_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lower_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lower_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.lower_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.lower_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.lower_table.setShowGrid(False)
        self.lower_table.setCornerButtonEnabled(False)
        self.lower_table.setRowCount(5)
        self.lower_table.setColumnCount(1)
        self.lower_table.horizontalHeader().setVisible(False)
        self.lower_table.horizontalHeader().setHighlightSections(False)
        self.lower_table.horizontalHeader().setStretchLastSection(True)
        self.lower_table.verticalHeader().setVisible(False)
        self.lower_table.verticalHeader().setHighlightSections(False)
        self.lower_table.verticalHeader().setStretchLastSection(False)

        self.horizontalLayout.addWidget(self.lower_table)

        self.metaicon_plot = PlotWidget(self.content_frame)
        self.metaicon_plot.setObjectName(u"metaicon_plot")
        self.metaicon_plot.setStyleSheet(u"background-color: #00000000")

        self.horizontalLayout.addWidget(self.metaicon_plot)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)


        self.verticalLayout_2.addLayout(self.horizontalLayout)


        self.verticalLayout.addWidget(self.content_frame)


        self.retranslateUi(MetaIcon)

        QMetaObject.connectSlotsByName(MetaIcon)
    # setupUi

    def retranslateUi(self, MetaIcon):
        MetaIcon.setWindowTitle(QCoreApplication.translate("MetaIcon", u"MetaIcon", None))
        self.minimizeButton.setText("")
        self.closeButton.setText("")

        __sortingEnabled = self.upper_table.isSortingEnabled()
        self.upper_table.setSortingEnabled(False)
        ___qtablewidgetitem = self.upper_table.item(0, 0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("MetaIcon", u".", None));
        ___qtablewidgetitem1 = self.upper_table.item(1, 0)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("MetaIcon", u".", None));
        ___qtablewidgetitem2 = self.upper_table.item(2, 0)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("MetaIcon", u".", None));
        ___qtablewidgetitem3 = self.upper_table.item(3, 0)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("MetaIcon", u".", None));
        self.upper_table.setSortingEnabled(__sortingEnabled)


        __sortingEnabled1 = self.lower_table.isSortingEnabled()
        self.lower_table.setSortingEnabled(False)
        ___qtablewidgetitem4 = self.lower_table.item(0, 0)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("MetaIcon", u"Azimuth", None));
        ___qtablewidgetitem5 = self.lower_table.item(1, 0)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("MetaIcon", u"Graze", None));
        ___qtablewidgetitem6 = self.lower_table.item(2, 0)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("MetaIcon", u"Layover", None));
        ___qtablewidgetitem7 = self.lower_table.item(3, 0)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("MetaIcon", u"Shadow", None));
        ___qtablewidgetitem8 = self.lower_table.item(4, 0)
        ___qtablewidgetitem8.setText(QCoreApplication.translate("MetaIcon", u"Multipath", None));
        self.lower_table.setSortingEnabled(__sortingEnabled1)

    # retranslateUi

