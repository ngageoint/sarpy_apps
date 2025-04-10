class ToolTips:

    def directories_buttons():
        return '''
        <p>This is the current directory</p>
        <p>Clicking a button opens its folder in the Directory Contents Pane.</p>
        <p>The text on the button corresponding to the open folder is displayed in bold.</p>
        '''
    def add_plot_button():
        return '''Creates a new empty plot'''
    
    class FileDialog:
        def favorite_directories_window():
            return '''
            <p><span>Displays favorite directories for quick and easy access.</span></p>
            <p><span>New favorites may be added by dragging-and-dropping a folder from the Directory Contents Pane. 
            Favorites maybe removed by right-clicking on a folder and selecting "remove".</span></p>
            <p><span>Favorites are automatically saved when the application closes.</span></p>
            <p><span>Double click on a folder to open its contents</span></p>
            '''

        def directory_contents_window():
            return '''
            <p><span>Displays the contents of the current directory.</span></p>
            <p><span>Double-clicking a folder in the pane will open that folder. Folders may be dragged-and-dropped into 
            the Favorites Directories Pane for easy access.</span></p>
            <p><span>A file in the pane may be opened in two ways:</span></p>
            <ul><li><u>Drag-and-Drop</u>: This opens the file in an existing plot. If there is already an image in the 
            plot, it is replaced. A plot must exist to be dropped into.</li>
            <li><u>Double-Click</u>: This creates a new plot and opens the file in that plot</li></ul>
            '''
        
        def file_type_filter():
            return '''
            <p>Chooses which file type filter to apply to the directory contents. 
            Additional filters may be added by editing the MITM configuration file.</p>
            '''
  
    class PlotWidgetDock:
        
        def coordinates():
            return '''
            <p>Displays coordinates under the mouse when it is hovering over the image.</p>
            <p>Click to cycle through the coordinate format options:</p>
            <ul><li>Degrees, Minutes, and Seconds</li>
            <li>Decimal Degrees</li>
            <li>Pixel Coordinates (X,Y)</li></ul>
            '''
        
        def downsample_method_combobox():
            return '''
            <p>Choose the downsampling method to use</p>
            '''
        
        def remap_method_combobox():
            return '''
            <p>Choose the remapping method to use</p>
            '''
        
        def aspect_ratio_combobox():
            return '''
            <p>Change the aspect ratio</p>
            '''
        
        def meta_icon_button():
            return '''
            <p>Display the MetaIcon for this plot</p>
            '''