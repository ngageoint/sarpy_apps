from distutils.core import setup

setup(name='python-mitm',
      version='1.0',
      description='Python More Image Than Memory',
      author='N-ASK Incorporated',
      author_email='',
      url='local repo',
      packages=['PyMITM','PyMITM.utils', 'PyMITM.resources'],
      package_data={"PyMITM.resources" : ["style.qss", "SoftwareUserManual.pdf"]},
      py_modules=['mitm_model', 'mitm_controller', 'mitm_viewer','mitm_subapplication', 'mitm_wrapper', 'ui_mitm_mainwindow', 'ui_plot_widget_dock', 'ui_wrapper']
     )