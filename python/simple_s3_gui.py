import ipywidgets as widgets
import batch_simple_2311 as bat

class S3_Browser:

    def __init__(self, bucket_dict, title="SIMPLE S3 Browser"):
        self.bucket_dict = bucket_dict
        #self.files = files
        self.title = title

        self.srce_bucket_ddlb = widgets.Dropdown(
            options=list(bucket_dict.keys()),
            description='Source Bucket:',
            disabled=False,
            layout={'width': 'auto'},
            style = {'description_width': 'initial'}
        )

        self.files, self.folders = self._list_s3_objects( self.srce_bucket_ddlb.value )
        self.srce_folder_ddlb = widgets.Dropdown(
            options=self.folders,
            description='Source Folder:',
            disabled=False,
            layout={'width': 'auto'},
            style = {'description_width': 'initial'}
        )
        self.objects_cbx_list = self._get_objects_cbx_list(self.files)        

        self.dest_bucket_ddlb = widgets.Dropdown(
            options=list(bucket_dict.keys()),
            description='Destination Bucket:',
            disabled=False,
            layout={'width': 'auto'},
            style = {'description_width': 'initial'}
        )
        #dest_files, self.dest_folders = self._list_s3_objects( self.dest_bucket_ddlb.value )
        self.dest_folder_ddlb = widgets.Dropdown(
           options=self.folders, # init same as srce folders
            description='Destination Folder:',
            disabled=False,
            layout={'width': 'auto'},
            style = {'description_width': 'initial'}
        )
        #self.objects_cbx_list = self._get_objects_cbx_list(self.files)        

        
        # Create Controls
        self.search_btn = widgets.Button(
            description='',
            disabled=True,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Find Ruleset by Name',
            icon='search', # (FontAwesome names without the `fa-` prefix),
            layout={'width': '40px'}
        )
        self.filter_text = widgets.Text(
            value='',
            placeholder='Type Substring to Filter Objects',
            description='Source Filter:',
            disabled=False ,
            style = dict(font_style = 'italic') # doesn't work 
        )
        self.copy_btn = widgets.Button(
            description='Copy',
            disabled=True,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Copy Selected Objects to Specified Folder',
            icon='clone' # (FontAwesome names without the `fa-` prefix)
        )
        self.move_btn = widgets.Button(
            description='Move',
            disabled=True,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Move Selected Objects to Specified Folder',
            icon='arrow-right' # (FontAwesome names without the `fa-` prefix)
        )
        self.rename_btn = widgets.Button(
            description='Rename',
            disabled=True,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Rename Selected Object',
            icon='edit' # (FontAwesome names without the `fa-` prefix)
        )
        self.delete_btn = widgets.Button(
            description='Delete',
            disabled=True,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Delete Selected Objects',
            icon='remove' # (FontAwesome names without the `fa-` prefix)
        )
        self.confirm_btn = widgets.Button(
            description='Confirm',
            disabled=True,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Confirm and Execute Action',
            icon='' # (FontAwesome names without the `fa-` prefix)
        )
        self.cancel_btn = widgets.Button(
            description='Cancel',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Cancel Action and Return to Previous View',
            icon='' # (FontAwesome names without the `fa-` prefix)
        )

        self.objects_vbox = widgets.VBox(
            self.objects_cbx_list, 
            layout=widgets.Layout(height='300px')
        )

        self.message_label = widgets.Label(
            value = "Selected Objects:"
        )

        self.message_textarea = widgets.Textarea (
            value='Hello World',
            placeholder='Type something',
            description='',
            disabled=False, 
            layout=widgets.Layout(width="100%", height='120px')   
        )

        self.status_text = widgets.Textarea(
            value='',
            placeholder='',
            description='',
            disabled=True ,
            layout=widgets.Layout(width="100%")
        )

        self.input_label = widgets.Label(
            value = "Enter Destination for Selected Objects:"
        )

        self.input_text = widgets.Text(
            value='',
            placeholder='s3://{bucket-name}/{prefix}/',
            description='',
            disabled=False ,
            layout=widgets.Layout(width="100%")
        )

        self.app_layout = None

        self.run_application()

    def generate_layout(self):

        self.header_pane = widgets.VBox( [
            widgets.HTML(value=f"<h1>{self.title}</h1>"),  #({self.rules_text.value.count()})</h2>"),
        ],
        layout=widgets.Layout(height='auto')  )

        # list S3 objects and action buttons
        self.object_pane = widgets.VBox( [
            widgets.HBox([self.srce_bucket_ddlb]),
            widgets.HBox([self.srce_folder_ddlb]),
            widgets.HBox([self.filter_text]),
            widgets.HBox([
                self.copy_btn,
                self.move_btn,
                self.rename_btn,
                self.delete_btn
            ]),
            self.objects_vbox ], 
            layout=widgets.Layout(height='auto')
        )

        # show selected objects, confirm/cancel action
        self.action_pane = widgets.VBox ( [
            self.message_label,
            self.message_textarea,
            self.input_label,
            self.dest_bucket_ddlb,
            self.dest_folder_ddlb,
            self.input_text,
            widgets.HBox ( [
                self.confirm_btn,
                self.cancel_btn
            ]) ], 
            layout=widgets.Layout(height='auto')
        )

        self.app_layout = widgets.AppLayout(
            header = self.header_pane,
            left_sidebar = None,
            center = self.object_pane, # default
            right_sidebar = None,
            footer = self.status_text
        )

        return self.app_layout

    def run_application(self):
        self.setup_event_handlers()
        display(self.generate_layout())
        self._refresh_objects_vbox( self.objects_cbx_list )  

    def setup_event_handlers(self):
        self.srce_bucket_ddlb.observe(self.on_select_srce_bucket, names='value')
        self.srce_folder_ddlb.observe(self.on_select_srce_folder, names='value')
        self.dest_bucket_ddlb.observe(self.on_select_dest_bucket, names='value')
        self.dest_folder_ddlb.observe(self.on_select_dest_folder, names='value')
        self.filter_text.observe(self.on_change_filter_text, names='value')
        self.input_text.observe(self.on_change_input_text, names='value')
        self.copy_btn.on_click(self.on_click_copy_button)
        self.move_btn.on_click(self.on_click_move_button)
        self.rename_btn.on_click(self.on_click_rename_button)
        self.delete_btn.on_click(self.on_click_delete_button)
        self.confirm_btn.on_click(self.on_click_confirm_button)
        self.cancel_btn.on_click(self.on_click_cancel_button)

    # Callbacks
    def on_select_srce_bucket( self, *args):
        self.files,self.folders = self._list_s3_objects( self.srce_bucket_ddlb.value )
        self.srce_folder_ddlb.options = self.folders
        self.objects_cbx_list = self._get_objects_cbx_list(self.files)  
        self._refresh_objects_vbox( self.objects_cbx_list )

    def on_select_srce_folder( self, *args):
        #self.files,self.folders = self._list_s3_objects( self.srce_bucket_ddlb.value )
        self.objects_cbx_list = self._get_objects_cbx_list(self.files)  
        self._refresh_objects_vbox( self.objects_cbx_list )

    def on_select_dest_bucket( self, *args):
        dest_files,self.dest_folders = self._list_s3_objects( self.dest_bucket_ddlb.value )
        self.dest_folder_ddlb.options = self.dest_folders
        #self.objects_cbx_list = self._get_objects_cbx_list(self.files)  
        #self._refresh_objects_vbox( self.objects_cbx_list )

    def on_select_dest_folder( self, *args):
        self.input_text.value = self.dest_folder_ddlb.value
        #self.objects_cbx_list = self._get_objects_cbx_list(self.files)  
        #self._refresh_objects_vbox( self.objects_cbx_list )

    def on_change_filter_text( self, *args):
        import re
        pattern=self.filter_text.value
        reg = re.compile(pattern)
        self._refresh_objects_vbox( self._get_objects_cbx_list( list(filter(reg.search, self.files)) ))

        self._show_status(f"Filter Text Changed: {pattern}")

    def on_change_input_text( self, *args):
        self.confirm_btn.disabled = False

    def on_click_confirm_button( self, *args ):
        self._show_status("CONFIRM Button Clicked!" )

        for srce_objname in self._get_cbx_selected():
            bucket_name = srce_objname[:srce_objname.find('/')]
            srce_bucket = self.bucket_dict[bucket_name]

            srce_s3_client = bat.get_s3_client( 
                srce_bucket['Profile'], 
                srce_bucket['Region'], 
                **srce_bucket
            )
            if 'DELETE' in app.input_label.value:
                bat.delete_s3_object( srce_objname, srce_s3_client)
                continue

            # else read object into memory for RENAME, COPY, or MOVE ...
            # bat.get_virt_mem() # ToDo check if big enough
            fileobj = bat.get_s3_object( srce_objname, srce_s3_client )

            # ... and name the destination
            if 'NEW NAME' in app.input_label.value:
                srce_folder  = srce_objname[:srce_objname.rfind('/')+1]
                dest_objname = srce_folder + self.input_text.value
                #print (srce_folder, dest_objname)
            else: # COPY or MOVE
                dest_folder = self.input_text.value
                dest_objname = dest_folder + srce_objname.split('/')[-1]

            bucket_name = dest_objname[:dest_objname.find('/')]
            dest_bucket = self.bucket_dict[bucket_name]

            dest_s3_client = bat.get_s3_client( 
                dest_bucket['Profile'], 
                dest_bucket['Region'], 
                **dest_bucket
            )
            bat.put_s3_object( dest_objname, fileobj, dest_s3_client )

            # delete the source object unless it's a copy
            if not 'COPY' in app.input_label.value:
                bat.delete_s3_object( srce_objname, srce_s3_client )

    def on_click_cancel_button( self, *args ):
        self._show_status("CANCEL Button Clicked!" )
        self.app_layout.center = self.object_pane

    def on_change_objects( self, *args ):
        #self._show_status("Checkbox Clicked!")
        #self._show_status(str(self._get_cbx_selected()))
        self._get_cbx_selected()

    def on_click_copy_button( self, *args):
        self.message_label.value = "Selected Objects:"        
        self.message_textarea.value = "\n".join(self._get_cbx_selected())
        self.input_label.value = "Enter the COPY Destination for Selected Objects:"
        self._show_dest_ddlb( True ) 

        self.app_layout.center = self.action_pane

    def on_click_move_button( self, *args):
        self._show_status("MOVE Button Clicked!") 
        self.message_label.value = "Selected Objects:"        
        self.message_textarea.value = "\n".join(self._get_cbx_selected())
        self.input_label.value = "Enter the MOVE Destination for Selected Objects:"
        self._show_dest_ddlb( True ) 

        self.app_layout.center = self.action_pane

    def on_click_rename_button( self, *args):
        self._show_status("RENAME Button Clicked!" )          
        self.message_label.value = "Selected Object:"        
        self.message_textarea.value = "\n".join(self._get_cbx_selected())
        folder = self.message_textarea.value
        folder = folder[:folder.rfind('/')+1]
        self.input_label.value = f"Enter the NEW NAME for the Selected Object in Folder '{folder}':"
        self._show_input_text( self.message_textarea.value.split('/')[-1] )
        self._show_dest_ddlb( False ) 

        self.app_layout.center = self.action_pane

    def on_click_delete_button( self, *args):
        self._show_status("DELETE Button Clicked!")         
        self.message_label.value = "Selected Objects:"        
        self.message_textarea.value = "\n".join(self._get_cbx_selected())
        self.input_label.value = "Do you REALLY want to DELETE the Selected Objects ?"
        self._show_input_text( '' )
        self._show_dest_ddlb( False ) 

        self.app_layout.center = self.action_pane

    # Utilities
    def _show_dest_ddlb( self, show = True ):
        if show:
            self.dest_bucket_ddlb.layout.visibility = 'visible'
            self.dest_folder_ddlb.layout.visibility = 'visible'
            self.dest_bucket_ddlb.layout.height = '30px' 
            self.dest_folder_ddlb.layout.height = '30px' 
        else:
            self.dest_bucket_ddlb.layout.visibility = 'hidden' 
            self.dest_folder_ddlb.layout.visibility = 'hidden'
            self.dest_bucket_ddlb.layout.height = '0px' 
            self.dest_folder_ddlb.layout.height = '0px'             

    def _show_srce_ddlb( self, show = True ):
        if show:
            self.srce_bucket_ddlb.layout.visibility = 'visible'
            self.srce_folder_ddlb.layout.visibility = 'visible'
            self.filter_text.visibility = 'visible'
            self.srce_folder_ddlb.layout.height = '30px' 
            self.srce_folder_ddlb.layout.height = '30px' 
            self.filter_text.layout.height = '30px' 
        else:
            self.srce_bucket_ddlb.layout.visibility = 'hidden' 
            self.srce_folder_ddlb.layout.visibility = 'hidden'
            self.filter_text.layout.visibility = 'hidden'
            self.srce_bucket_ddlb.layout.height = '0px' 
            self.srce_folder_ddlb.layout.height = '0px'             
            self.filter_text.layout.height = '0px' 

    def _show_input_text( self, input_default):
        self.input_text.value = input_default
        if input_default:
            self.input_text.value = input_default
            self.input_text.layout.visibility = 'visible' 
            self.input_text.layout.height = '30px' 
        else:
            self.input_text.layout.visibility = 'hidden' 
            self.input_text.layout.height = '0px' 

    def _show_status(self, status_text):
        self.status_text.value = status_text
        print(status_text)

    def _get_objects_cbx_list( self, files ):
        cbx_files = []

        for file in files:
            if file.endswith('/'):
                continue

            if self.srce_folder_ddlb.value not in file:
                continue
            
            #else:
            cbx = widgets.Checkbox(
                value = False,
                description = file,
                disabled = False,
                indent = False,
                layout=widgets.Layout(width="100%", height='12px')
            )
            cbx_files.append ( cbx )

        #return widgets.VBox(cbx_files, layout=widgets.Layout(height='200px'))
        #self.objects_vbox.layout.height= f"{len(self.objects_cbx_list)*20}px"
        return cbx_files

    def _list_s3_objects( self, bucket_name, pattern = '.' ):
        bucket = self.bucket_dict[bucket_name]

        s3_client = bat.get_s3_client( 
            bucket['Profile'], 
            bucket['Region'], 
            **bucket
        )
        files = bat.get_namelist_by_S3pattern( 
            s3_bucket = bucket['BucketName'], 
            pattern = pattern, 
            Folder = bucket['Folders'][0],
            ExpandFolders = True,
            S3Client = s3_client )
        
        folders = bat.get_namelist_by_S3pattern( 
            s3_bucket = bucket['BucketName'], 
            pattern = '.', 
            Folder = bucket['Folders'][0],
            S3Client = s3_client )
        
        return files,folders

    def _refresh_objects_vbox( self, objects_cbx_list  ):
        self.objects_vbox.children = objects_cbx_list
        self.objects_vbox.layout.height= f"{(len(objects_cbx_list)+1)*20}px"
        for cbx in self.objects_vbox.children:
            cbx.observe(self.on_change_objects)

    def _get_cbx_selected( self ):
        cbx_selected = []
        for cbx in self.objects_vbox.children:
            if cbx.value:
                cbx_selected.append( cbx.description )

        if len(cbx_selected) == 0:
            self.copy_btn.disabled = True
            self.move_btn.disabled = True
            self.rename_btn.disabled = True
            self.delete_btn.disabled = True

        if len(cbx_selected) == 1:
            self.copy_btn.disabled = False
            self.move_btn.disabled = False
            self.rename_btn.disabled = False
            self.delete_btn.disabled = False

        if len(cbx_selected) > 1:
            self.rename_btn.disabled = True

        return cbx_selected
