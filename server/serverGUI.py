import tkinter
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import calendar
import datetime
from collections import namedtuple
import server.serverDB as serverDB
import matplotlib

matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa
from matplotlib.figure import Figure  # noqa

# sensor -> table_name, mode -> (daily, hourly, minutely), datetime -> (either Date, Date or Date, Shift or Date, Hour)
plotSetting = namedtuple('plotSetting', ['machine', 'mode', 'details'])


class MainWindow(ttk.Frame):
    NUM_COL = 2

    def __init__(self, parent, save: serverDB.ServerSettings, **kwargs):
        self.save = save
        ttk.Frame.__init__(self, parent, **kwargs)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=100)
        self.columnconfigure(0, weight=1)
        self.database = serverDB.DatabaseManager(save)
        self.configuration_settings = None

        # MenuBar
        self.menu_bar = tkinter.Menu(self.master)
        settings = tkinter.Menu(self.menu_bar, tearoff=0)
        settings.add_command(label='Settings', command=self.launch_settings)
        self.menu_bar.add_cascade(label='Settings', menu=settings)
        self.master.config(menu=self.menu_bar)

        # Top Frame settings
        self.top_frame = ttk.Frame(self, relief='raise', borderwidth=2)
        self.top_frame.grid(row=0, column=0, sticky='nsew')
        self.top_frame.columnconfigure(0, weight=1, uniform='equalWidth')
        self.top_frame.columnconfigure(1, weight=1, uniform='equalWidth')
        self.top_frame.columnconfigure(2, weight=1, uniform='equalWidth')
        self.top_frame.rowconfigure(0, weight=1)
        self.top_frame.rowconfigure(1, weight=2)
        self.request_interval = tkinter.StringVar()
        self.request_interval.set('Requesting every {} minutes'.format(
            self.save.misc_settings[self.save.REQUEST_TIME]))
        request_label = ttk.Label(self.top_frame, textvariable=self.request_interval)
        request_label.grid(row=0, column=0, sticky='w')
        request_button = ttk.Button(self.top_frame, text='Request now')  # TODO add command
        request_button.grid(row=0, column=1)
        plot_button = ttk.Button(self.top_frame, text='Plot new', command=self.launch_plot_new)
        plot_button.grid(row=0, column=2)
        self.quick_frame = None
        self.quick_access_setup()

        # Notebook setup
        self.view_notebook = NotebookView(self, save)
        self.view_notebook.grid(row=1, column=0, sticky='nsew')
        self.populate_graph_treeview()
        self.plot_graph_add_treeview()
        # TODO apschduler to refresh/animate the live graphs
        # TODO setup save_settings to change apscheduler in communication

    def quick_access_setup(self):
        if self.quick_frame is not None:
            self.quick_frame.destroy()
        self.quick_frame = ttk.LabelFrame(self.top_frame, text='Quick Access: ')
        self.quick_frame.grid(row=1, column=0, columnspan=3, sticky='nsew')
        if len(self.save.quick_access) < 1:
            label = ttk.Label(self.quick_frame, text='Set up quick access in Settings')
            label.pack()
        else:
            num_col = MainWindow.NUM_COL
            for col in range(num_col):
                self.quick_frame.columnconfigure(col, weight=1)
            keys = list(self.save.quick_access.keys())
            for index in range(len(self.save.quick_access)):
                row = index//num_col
                col = index % num_col
                key = keys[index]
                value = self.save.quick_access[key]
                button = ttk.Button(self.quick_frame, text=key, command=lambda text=key, settings=value:
                                    self.launch_quick_plot(text, settings))
                button.grid(row=row, column=col)

    def launch_quick_plot(self, button, settings):
        graph_detail_view = tkinter.Toplevel(self.master)
        graph_detail_view.title(button)
        gdv_frame = GraphDetailView(graph_detail_view, self.database, data=settings, save=self.save)
        gdv_frame.pack(fill=tkinter.BOTH, expand=tkinter.TRUE)

    def launch_plot_new(self):
        plot_settings = tkinter.Toplevel(self.master)
        plot_settings.title('Plot New')
        plot_settings.geometry('-200-200')
        plot_settings_frame = GraphDetailSettingsPage(plot_settings, self.save, self.database)
        plot_settings_frame.pack(fill=tkinter.BOTH, expand=tkinter.TRUE)
        plot_settings.grab_set()

    def populate_graph_treeview(self):
        # Draw Graph Canvas
        database_name = datetime.datetime.today().strftime('%m_%B_%Y.sqlite')
        tables = self.database.get_table_names(database_name)
        self.view_notebook.graph_canvas.set_total_plots(len(tables))

    def plot_graph_add_treeview(self):
        now = datetime.datetime.now()
        database_name = now.strftime('%m_%B_%Y.sqlite')
        # Get current shift
        shift_name, shift_start, shift_end = self.get_shift(now)
        tables = self.database.get_table_names(database_name)
        if len(tables) != self.view_notebook.graph_canvas.total_plots:
            self.populate_graph_treeview()
            return
        self.view_notebook.treeview.delete(*self.view_notebook.treeview.get_children())
        for index in range(self.view_notebook.graph_canvas.total_plots):
            table = tables[index]
            title = '{}\n{}   {}'.format(table, shift_name, now.strftime('%Y-%m-%d'))
            time_list, count_list = self.database.get_sums(table, shift_start, shift_end, 'Hourly')
            self.view_notebook.graph_canvas.plot(index, x=time_list, y=count_list, x_format='%H:%M', title=table)
            for pos in range(len(time_list)):
                self.view_notebook.treeview.insert('', tkinter.END, values=(table, count_list[pos], time_list[pos]))

    def get_shift(self, date_time):
        date = date_time.strftime('%Y-%m-%d')
        for name, (start, duration) in self.save.shift_settings.items():
            start_date = datetime.datetime.strptime(' '.join([date, start]), '%Y-%m-%d %H:%M')
            end_date = start_date + datetime.timedelta(seconds=duration)
            if start_date <= date_time < end_date:
                return name, start_date, end_date

        start_date = date_time.replace(minute=0, second=0, microsecond=0)
        end_date = start_date + datetime.timedelta(hours=1)
        return date_time.strftime('Hour %H:00'), start_date, end_date

    def launch_settings(self):
        if self.configuration_settings is not None:
            self.configuration_settings.lift()
            return
        self.configuration_settings = tkinter.Toplevel(self)
        self.configuration_settings.title('Configuration & Settings')
        self.configuration_settings.geometry('-200-200')
        configuration_settings_frame = ConfigurationSettings(self.configuration_settings, self.save, self.database,
                                                             self.request_interval)
        configuration_settings_frame.pack(fill=tkinter.BOTH, expand=tkinter.TRUE)
        configuration_settings_frame.grab_set()


class NotebookView(ttk.Notebook):
    NUM_COL = 2

    def __init__(self, parent, database, data=None, save=None, **kwargs):
        ttk.Notebook.__init__(self, parent, **kwargs)
        self.database = database
        self.save = save
        self.data = data
        self.num_col = NotebookView.NUM_COL
        # Graph
        self.graph_frame = VerticalScrollFrame(self)
        self.graph_frame.grid(sticky='nsew')
        self.graph_canvas = GraphCanvas(self.graph_frame.get_interior_frame())
        self.graph_canvas.pack(fill=tkinter.BOTH, expand=tkinter.TRUE)
        self.add(self.graph_frame, text='Graph')
        # TreeView Frame
        treeview_frame = ttk.Frame(self)
        treeview_frame.grid(sticky='nsew', padx=5, pady=5)
        self.add(treeview_frame, text='Details')
        treeview_frame.rowconfigure(0, weight=1)
        treeview_frame.columnconfigure(0, weight=1)
        treeview_frame.columnconfigure(1, weight=0)
        # TreeView
        self.treeview = ttk.Treeview(treeview_frame)
        self.treeview.grid(row=0, column=0, sticky='nsew')
        self.treeview['show'] = 'headings'
        self.treeview['column'] = ('machine', 'count', 'timestamp')
        self.treeview.heading('machine', text='Machine', command=lambda: self.sort_tree_view('machine', False))
        self.treeview.heading('count', text='Count', command=lambda: self.sort_tree_view('count', False))
        self.treeview.heading('timestamp', text='Timestamp', command=lambda: self.sort_tree_view('timestamp', False))
        self.treeview.column('machine', width=100)
        self.treeview.column('count', width=60, anchor=tkinter.E)
        self.treeview.column('timestamp', width=70)
        # Scroll for Treeview
        treeview_v_scroll = ttk.Scrollbar(treeview_frame, orient='vertical', command=self.treeview.yview)
        treeview_v_scroll.grid(row=0, column=1, sticky='nsw')
        self.treeview.configure(yscrollcommand=treeview_v_scroll.set)

        if self.data is not None and self.save is not None:
            if len(self.data) < self.num_col:
                self.num_col = 1
            self.graph_treeview_populate(self.data)

    def graph_treeview_populate(self, data):
        data_keys = list(data.keys())
        self.graph_canvas.set_total_plots(len(data))
        for index in range(len(data)):
            graph = data_keys[index]
            machine_list, mode, (detail1, detail2) = data[graph]
            date_format = '%Y-%m-%\n%H:%M'
            inverse = False
            legend_list = []

            for position in range(len(machine_list)):
                _temp_out = self.get_data_from_database(machine=machine_list[position], mode=mode, detail1=detail1,
                                                        detail2=detail2, save=self.save)
                machine, title, date_list, date_format, count_list = _temp_out
                self.graph_canvas.plot(index, date_list, count_list)
                legend_list.append('{} - {}'.format(machine, sum(count_list)))
                # Treeview
                for pos in range(len(date_list)):
                    self.treeview.insert('', tkinter.END, values=(machine, count_list[pos], date_list[pos]))

            x_label = '{} \u27A1 {}'.format(detail1, detail2)
            if mode == 'Daily':
                inverse = True
            self.graph_canvas.format_subplot(index, x_format=date_format, title=graph, legend=legend_list,
                                             x_label=x_label, invert_x=inverse)

        self.graph_canvas.show()

    def get_data_from_database(self, machine, mode, detail1, detail2, save):
        if detail2 == 'Current day':
            detail2 = datetime.datetime.now()
            detail1 = detail2 - datetime.timedelta(days=6)
            detail2 = detail2.strftime('%Y-%m-%d')
            detail1 = detail1.strftime('%Y-%m-%d')
        elif detail2 == 'Previous day':
            detail2 = datetime.datetime.now() - datetime.timedelta(days=1)
            detail1 = detail2 - datetime.timedelta(days=6)
            detail2 = detail2.strftime('%Y-%m-%d')
            detail1 = detail1.strftime('%Y-%m-%d')
        elif detail1 == 'Current day':
            detail1 = datetime.datetime.now().strftime('%Y-%m-%d')
        elif detail1 == 'Previous day':
            detail1 = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        date_format = '%H:%M'
        if mode == 'Daily':
            start_date = datetime.datetime.strptime(detail1, '%Y-%m-%d')
            end_date = datetime.datetime.strptime(detail2, '%Y-%m-%d')
            date_format = '%d'
        elif mode == 'Hourly':
            start_time, duration = save.shift_settings[detail2]
            start_date = datetime.datetime.strptime(' '.join([detail1, start_time]), '%Y-%m-%d %H:%M')
            end_date = start_date + datetime.timedelta(seconds=duration)
        else:
            start_date = datetime.datetime.strptime(' '.join([detail1, detail2]), '%Y-%m-%d %H:%M')
            end_date = start_date + datetime.timedelta(hours=1)

        date_list, count_list = self.database.get_sums(machine, start_date, end_date, mode)

        title = '{}\n{} - {}'.format(machine, detail1, detail2)
        return machine, title, date_list, date_format, count_list

    def sort_tree_view(self, column, reverse):
        item_list = [(self.treeview.set(_iid, column=column), _iid) for _iid in self.treeview.get_children()]
        item_list.sort(reverse=reverse)
        # Arrange the tree_view based on item_list
        for index, (value, _iid) in enumerate(item_list):
            self.treeview.move(_iid, '', index)

        self.treeview.heading(column, command=lambda col=column: self.sort_tree_view(col, not reverse))


class GraphDetailView(ttk.Frame):

    def __init__(self, parent, database, data=None, save=None, **kwargs):
        ttk.Frame.__init__(self, parent, **kwargs)
        self.master.minsize(width=1000, height=400)

        # Notebook setup
        view_notebook = NotebookView(self, database, data=data, save=save)
        view_notebook.pack(fill=tkinter.BOTH, expand=tkinter.TRUE)


class GraphDetailSettingsPage(ttk.Frame):
    MAX_PLOTS = 5
    MAX_GRAPHS = 6

    def __init__(self, parent, save: serverDB.ServerSettings, database: serverDB.DatabaseManager, quick_tv=None,
                 **kwargs):
        self.save = save
        self.database = database
        ttk.Frame.__init__(self, parent, **kwargs)
        self.plot_settings = {}
        self.rowconfigure(4, weight=1)
        self.columnconfigure(0, weight=1)
        self.quick_tv = quick_tv
        self.label_width = 8
        self.widgets1 = []
        self.widgets2 = []
        # Quick Access Button Name
        if self.quick_tv:
            name_validation = self.register(GraphDetailSettingsPage.validate_name)
            quick_frame = ttk.Frame(self)
            quick_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
            quick_frame.columnconfigure(1, weight=1)
            quick_label = ttk.Label(quick_frame, text='Name: ', width=self.label_width)
            quick_label.grid(row=0, column=0, sticky='e')
            self.quick_entry = ttk.Entry(quick_frame, validate='key', validatecommand=(name_validation, '%P'))
            self.quick_entry.grid(row=0, column=1, sticky='w')
            self.quick_entry.focus_set()
        # New
        choice_frame = ttk.Frame(self)
        choice_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        choice_frame.columnconfigure(1, weight=1)
        # Graph Name
        graph_label = ttk.Label(choice_frame, text='Graph: ', width=self.label_width)
        graph_label.grid(row=0, column=0, sticky='e')
        self.graph_var = tkinter.StringVar()
        graph_validation = self.register(self.validate_graph_name)
        self.graph_combo = ttk.Combobox(choice_frame, textvariable=self.graph_var, postcommand=self.set_graph_values,
                                        validate='focus', validatecommand=(graph_validation, '%P', '%V'))
        self.graph_combo.grid(row=0, column=1, sticky='w')
        sensor_label = ttk.Label(choice_frame, text='Sensor: ', width=self.label_width)
        sensor_label.grid(row=1, column=0, sticky='e')
        self.sensor_var = tkinter.StringVar()
        database_name = datetime.datetime.now().strftime('%m_%B_%Y.sqlite')
        sensor_list = self.database.get_table_names(database_name)
        self.sensor_var.set(sensor_list[0])
        sensor_option = ttk.OptionMenu(choice_frame, self.sensor_var, self.sensor_var.get(), *sensor_list)
        sensor_option.grid(row=1, column=1, sticky='w')
        mode_label = ttk.Label(choice_frame, text='Mode: ', width=self.label_width)
        mode_label.grid(row=2, column=0, sticky='e')
        mode_list = ['Daily', 'Hourly', 'Minutely']
        self.mode_var = tkinter.StringVar()
        self.mode_var.set(mode_list[0])
        mode_menu = ttk.OptionMenu(choice_frame, self.mode_var, self.mode_var.get(), *mode_list,
                                   command=self.set_mutable_frame)
        mode_menu.grid(row=2, column=1, sticky='ew')
        self.widgets1.append(mode_menu)
        # Mutable options
        self.mutable_frame = None
        self.detail1_var = tkinter.StringVar()
        self.detail2_var = tkinter.StringVar()
        self.set_mutable_frame()
        # Current & Add Buttons
        current_add_frame = ttk.Frame(self)
        current_add_frame.grid(row=3, column=0, padx=5, pady=5, sticky='nsew')
        add_button = ttk.Button(current_add_frame, text='Add', command=self.add_plot_settings)
        add_button.pack(side=tkinter.RIGHT)
        current_button = ttk.Button(current_add_frame, text='Current', command=self.current_pressed)
        current_button.pack(side=tkinter.RIGHT, padx=(5, 20))
        self.widgets1.append(current_button)
        prev_button = ttk.Button(current_add_frame, text='Previous', command=self.previous_pressed)
        prev_button.pack(side=tkinter.RIGHT)
        self.widgets1.append(prev_button)
        # Graphs setting
        data_frame = ttk.Frame(self)
        data_frame.grid(row=4, column=0, sticky='nsew', padx=5, pady=5)
        data_frame.columnconfigure(0, weight=1)
        data_frame.rowconfigure(0, weight=1)
        self.data_treeview = ttk.Treeview(data_frame)
        self.data_treeview.grid(row=0, column=0, sticky='nsew')
        # Scroll for Treeview
        data_tv_v_scroll = ttk.Scrollbar(data_frame, orient='vertical', command=self.data_treeview.yview)
        data_tv_v_scroll.grid(row=0, column=1, sticky='nsw')
        self.data_treeview.configure(yscrollcommand=data_tv_v_scroll.set)
        self.data_treeview['column'] = ('mode', 'detail')
        self.data_treeview.heading('#0', text='Machine')
        self.data_treeview.heading('mode', text='Mode')
        self.data_treeview.heading('detail', text='Details')
        self.data_treeview.column('#0', width=150)
        self.data_treeview.column('mode', width=50)
        self.data_treeview.column('detail', width=200)
        # Treeview buttons
        button_frame = ttk.Frame(data_frame)
        button_frame.grid(row=0, column=2)
        up_button = ttk.Button(button_frame, text='\u25B2', command=lambda: self.move_item(-1))
        up_button.pack(side=tkinter.TOP)
        down_button = ttk.Button(button_frame, text='\u25BC', command=lambda: self.move_item(1))
        down_button.pack(side=tkinter.TOP)
        delete_button = ttk.Button(button_frame, text='Delete', command=self.delete_item)
        delete_button.pack(side=tkinter.TOP, pady=(20, 0))

        # Okay & Cancel Buttons
        button_frame = ttk.Frame(self)
        button_frame.grid(row=5, column=0, sticky='nsew', padx=5, pady=5)
        if self.quick_tv:
            save_button = ttk.Button(button_frame, text='Save', command=self.save_plot_settings)
            save_button.pack(side=tkinter.RIGHT)
        else:
            plot_button = ttk.Button(button_frame, text='Plot', command=self.launch_graph_detail_view)
            plot_button.pack(side=tkinter.RIGHT)
        cancel_button = ttk.Button(button_frame, text='Cancel', command=self.master.destroy)
        cancel_button.pack(side=tkinter.RIGHT)

    def set_mutable_frame(self, _selected=None):
        if self.mutable_frame is not None:
            self.mutable_frame.destroy()
        self.mutable_frame = ttk.Frame(self)
        self.mutable_frame.grid(row=2, column=0, sticky='nsew', padx=5, pady=5)
        self.mutable_frame.columnconfigure(1, weight=1)
        self.mutable_frame.columnconfigure(2, weight=1)
        self.detail1_var.set('')
        self.detail2_var.set('')
        self.widgets2.clear()
        if self.mode_var.get() == 'Daily':
            from_label = ttk.Label(self.mutable_frame, text='From: ', width=self.label_width)
            from_label.grid(row=0, column=0, sticky='e')
            from_entry = ttk.Entry(self.mutable_frame, textvariable=self.detail1_var, state=tkinter.DISABLED)
            from_entry.grid(row=0, column=1, sticky='w')
            from_calendar = ttk.Button(self.mutable_frame, text=u'\u2380',
                                       command=lambda: self.launch_calendar(self.detail1_var))
            from_calendar.grid(row=0, column=2, sticky='w')
            self.widgets2.append(from_calendar)
            to_label = ttk.Label(self.mutable_frame, text='To: ', width=self.label_width)
            to_label.grid(row=1, column=0, sticky='e')
            to_entry = ttk.Entry(self.mutable_frame, textvariable=self.detail2_var, state=tkinter.DISABLED)
            to_entry.grid(row=1, column=1, sticky='w')
            to_calendar = ttk.Button(self.mutable_frame, text=u'\u2380',
                                     command=lambda: self.launch_calendar(self.detail2_var))
            to_calendar.grid(row=1, column=2, sticky='w')
            self.widgets2.append(to_calendar)
        elif self.mode_var.get() == 'Hourly':
            date_label = ttk.Label(self.mutable_frame, text='Date: ', width=self.label_width)
            date_label.grid(row=0, column=0, sticky='e')
            date_entry = ttk.Entry(self.mutable_frame, textvariable=self.detail1_var, state=tkinter.DISABLED)
            date_entry.grid(row=0, column=1, sticky='w')
            date_calendar = ttk.Button(self.mutable_frame, text=u'\u2380',
                                       command=lambda: self.launch_calendar(self.detail1_var))
            date_calendar.grid(row=0, column=2, sticky='w')
            self.widgets2.append(date_calendar)
            shift_label = ttk.Label(self.mutable_frame, text='Shift: ', width=self.label_width)
            shift_label.grid(row=1, column=0, sticky='e')
            shift_list = list(self.save.shift_settings.keys())
            self.detail2_var.set(shift_list[0])
            shift_option = ttk.OptionMenu(self.mutable_frame, self.detail2_var, self.detail2_var.get(), *shift_list)
            shift_option.grid(row=1, column=1, sticky='w')
            self.widgets2.append(shift_option)
        elif self.mode_var.get() == 'Minutely':
            date_label = ttk.Label(self.mutable_frame, text='Date: ', width=self.label_width)
            date_label.grid(row=0, column=0, sticky='e')
            date_entry = ttk.Entry(self.mutable_frame, textvariable=self.detail1_var, state=tkinter.DISABLED)
            date_entry.grid(row=0, column=1, sticky='w')
            date_calendar = ttk.Button(self.mutable_frame, text=u'\u2380',
                                       command=lambda: self.launch_calendar(self.detail1_var))
            date_calendar.grid(row=0, column=2, sticky='w')
            self.widgets2.append(date_calendar)
            hour_label = ttk.Label(self.mutable_frame, text='Hour: ', width=self.label_width)
            hour_label.grid(row=1, column=0, sticky='e')
            hour_list = [('{}:00'.format(str(i).zfill(2))) for i in range(24)]
            self.detail2_var.set(hour_list[0])
            hour_option = ttk.OptionMenu(self.mutable_frame, self.detail2_var, self.detail2_var.get(), *hour_list)
            hour_option.grid(row=1, column=1, sticky='w')
            self.widgets2.append(hour_option)

    def current_pressed(self):
        if self.mode_var.get() == 'Daily':
            self.detail2_var.set('Current day')
            self.detail1_var.set('7 days ago')
        elif self.mode_var.get() == 'Hourly':
            self.detail1_var.set('Current day')
        elif self.mode_var.get() == 'Minutely':
            self.detail1_var.set('Current day')

    def previous_pressed(self):
        if self.mode_var.get() == 'Daily':
            self.detail2_var.set('Previous day')
            self.detail1_var.set('8 days ago')
        elif self.mode_var.get() == 'Hourly':
            self.detail1_var.set('Previous day')
        elif self.mode_var.get() == 'Minutely':
            self.detail1_var.set('Previous day')

    def launch_calendar(self, variable):
        calendar_pop = tkinter.Toplevel(self.master)
        calendar_pop.title('Select date')
        calendar_pop.resizable(False, False)
        calendar_pop_frame = CalendarPop(calendar_pop, variable)
        calendar_pop_frame.pack(fill=tkinter.X, expand=tkinter.TRUE)
        calendar_pop.grab_set()

    def set_graph_values(self):
        self.graph_combo.configure(values=self.data_treeview.get_children())

    def validate_graph_name(self, graph, _reason):
        if graph == '':
            return False

        if self.data_treeview.exists(graph):
            mode, details = self.data_treeview.item(graph)['values']
            details = details.split(' \u27A1 ')
            detail1 = details[0]
            detail2 = details[1]
            self.mode_var.set(mode)
            self.set_mutable_frame()
            self.detail1_var.set(detail1)
            self.detail2_var.set(detail2)
            for widget in self.widgets1 + self.widgets2:
                widget.state(('disabled', ))
        else:
            for widget in self.widgets1:
                widget.state(('!disabled', ))
            self.set_mutable_frame()

        return True

    def add_plot_settings(self):
        graph_name = self.graph_var.get()
        if graph_name == '' or self.detail1_var.get() == '' or self.detail2_var.get() == '':
            return
        # Checks if graph name exist
        if not self.data_treeview.exists(graph_name):
            # Maximum of 6 graphs per view
            if len(self.data_treeview.get_children('')) >= self.MAX_GRAPHS:
                messagebox.showinfo(title='Excess', message='Maximum of {} graphs per view'.format(self.MAX_GRAPHS))
                return

            details = ' \u27A1 '.join([self.detail1_var.get(), self.detail2_var.get()])
            self.data_treeview.insert('', tkinter.END, iid=graph_name, text=graph_name,
                                      values=(self.mode_var.get(), details), tag=('graph', ), open=True)
            self.validate_graph_name(graph_name, 'Add')
        # Maximum of 5 plots per view otherwise too messy
        if len(self.data_treeview.get_children(graph_name)) >= self.MAX_PLOTS:
            messagebox.showinfo(title='Excess', message='Maximum of {} plots per graph'.format(self.MAX_PLOTS))
            return

        self.data_treeview.insert(graph_name, tkinter.END, text=self.sensor_var.get())

    def move_item(self, direction):
        item = self.data_treeview.focus()
        if item != '':
            index = self.data_treeview.index(item) + direction
            self.data_treeview.move(item, self.data_treeview.parent(item), index)

    def delete_item(self):
        item = self.data_treeview.focus()
        if item != '':
            self.data_treeview.delete(item)

    def tree_view_to_plot_settings(self):
        self.plot_settings.clear()
        for graph in self.data_treeview.get_children():
            mode, detail = self.data_treeview.item(graph)['values']
            detail = detail.split(' \u27A1 ')
            detail1 = detail[0]
            detail2 = detail[1]
            machine_list = []
            for iid in self.data_treeview.get_children(graph):
                machine_list.append(self.data_treeview.item(iid)['text'])
            self.plot_settings[graph] = plotSetting(machine_list, mode, (detail1, detail2))

    def launch_graph_detail_view(self):
        self.tree_view_to_plot_settings()
        if len(self.plot_settings) < 1:
            return
        graph_detail_view = tkinter.Toplevel(self.master.master)
        graph_detail_view.title('Plot')
        gdv_frame = GraphDetailView(graph_detail_view, self.database, data=self.plot_settings, save=self.save)
        gdv_frame.pack(fill=tkinter.BOTH, expand=tkinter.TRUE)

        self.quit_parent()

    def save_plot_settings(self):
        self.tree_view_to_plot_settings()
        if len(self.plot_settings) < 1:
            return

        _iid = self.quick_tv.insert('', tkinter.END, text=self.quick_entry.get(), tag=('top', ), open=True)
        for graph, (machine_list, mode, detail) in self.plot_settings.items():
            details = ' \u27A1 '.join(detail)
            graph_iid = self.quick_tv.insert(_iid, tkinter.END, text=graph, values=(mode, details))
            for machine in machine_list:
                self.quick_tv.insert(graph_iid, tkinter.END, text=machine)

        self.quit_parent()

    def quit_parent(self):
        self.master.destroy()

    @staticmethod
    def validate_name(values):
        if len(values) > 15:
            return False
        else:
            return True


class VerticalScrollFrame(ttk.Frame):

    def __init__(self, parent, **kwargs):
        ttk.Frame.__init__(self, parent, **kwargs)
        self.canvas = tkinter.Canvas(self)
        self.canvas.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=tkinter.TRUE)
        v_scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        v_scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y, expand=tkinter.FALSE)
        self.canvas.config(yscrollcommand=v_scrollbar.set, scrollregion=self.canvas.bbox('all'))

        self.interior_frame = ttk.Frame(self.canvas)
        self.interior_frame_id = self.canvas.create_window((0, 0), window=self.interior_frame, anchor=tkinter.NW)

        self.interior_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)

    def _on_canvas_configure(self, event):
        canvas_width = event.width
        self.canvas.itemconfig(self.interior_frame_id, width=canvas_width)

    def _on_frame_configure(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def get_interior_frame(self):
        return self.interior_frame


class GraphCanvas(FigureCanvasTkAgg):
    NUM_COL = 2

    def __init__(self, parent, total_plots=1, title=None, x_format=None, x=None, y=None):
        self.figure = Figure()
        self.figure.set_tight_layout(True)
        self.num_col = GraphCanvas.NUM_COL
        self.num_row = GraphCanvas.NUM_COL
        self.subplots = []
        self.total_plots = total_plots
        self.set_total_plots(total_plots)
        FigureCanvasTkAgg.__init__(self, self.figure, parent)
        if title is not None:
            self.plot(x_format, x, y, title=title)

    def grid(self, **kwargs):
        self.get_tk_widget().grid(**kwargs)

    def pack(self, **kwargs):
        self.get_tk_widget().pack(**kwargs)

    def plot(self, plot_num, x, y, x_format=None, title=None):
        subplot = self.subplots[plot_num]

        subplot.plot(x, y, '-o')
        subplot.grid(linestyle='dashed')

        self.format_subplot(plot_num=plot_num, x_format=x_format, title=title)

        subplot.grid(linestyle='dashed')

    def clear_all_subplots(self):
        for subplot in self.subplots:
            subplot.clear()

    def format_subplot(self, plot_num, x_format=None, title=None, legend=None, x_label=None, invert_x=False):
        subplot = self.subplots[plot_num]

        if invert_x:
            subplot.invert_xaxis()

        if x_label:
            subplot.set_xlabel(x_label)

        if legend:
            subplot.legend(legend)

        if title:
            subplot.set_title(title)

        # Format tick location and label
        if x_format:
            x = subplot.lines[0].get_xdata()
            tick_num = len(x)//5
            if tick_num == 0:
                tick_num = 1
            subplot.set_xticks(x[0::tick_num])
            date_label = []
            for date in x[0::tick_num]:
                date_label.append(date.strftime(x_format))
            subplot.set_xticklabels(date_label)

    def set_total_plots(self, total_plots):
        self.figure.clear()
        self.subplots.clear()
        self.total_plots = total_plots
        # Reset num_row & num_col
        self.num_row = (self.total_plots - 1)//2 + 1
        self.num_col = GraphCanvas.NUM_COL
        self.figure.set_figheight(self.num_row*10, forward=True)
        if self.total_plots < self.num_col:
            self.num_col = 1

        for loc in range(self.total_plots):
            pos = loc + 1
            self.subplots.append(self.figure.add_subplot(self.num_row, self.num_col, pos))


class CalendarPop(tkinter.Frame):
    DAYS_A_WEEK = 7

    def __init__(self, parent, variable):
        self.variable = variable
        today = datetime.date.today()
        self._date = datetime.date(today.year, today.month, 1)
        tkinter.Frame.__init__(self, parent, padx=5, pady=5)
        self.columnconfigure(0, weight=0, uniform='equalWidth')
        self.columnconfigure(1, weight=0, uniform='equalWidth')
        self.columnconfigure(2, weight=0, uniform='equalWidth')
        self.columnconfigure(3, weight=0, uniform='equalWidth')
        self.columnconfigure(4, weight=0, uniform='equalWidth')
        self.columnconfigure(5, weight=0, uniform='equalWidth')
        self.columnconfigure(6, weight=0, uniform='equalWidth')
        left_button = tkinter.Button(self, text=u'\u25C0', width=3, command=self._prev_month)
        left_button.grid(row=0, column=0)
        right_button = tkinter.Button(self, text=u'\u25B6', width=3, command=self._next_month)
        right_button.grid(row=0, column=6)
        self.month_var = tkinter.StringVar()
        self.month_var.set(self._date.strftime('%B %Y'))
        month_label = tkinter.Label(self, textvariable=self.month_var)
        month_label.grid(row=0, column=1, columnspan=5)
        self._calendar = calendar.TextCalendar()
        header = [day for day in self._calendar.formatweekheader(3).split(' ')]
        for index in range(CalendarPop.DAYS_A_WEEK):
            header_label = tkinter.Label(self, text=header[index], background='red', foreground='white', width=4)
            header_label.grid(row=1, column=index)
        self.day_buttons = []
        self._update_calendar()

    def _update_calendar(self):
        for button in self.day_buttons:
            button.destroy()
        month = self._calendar.monthdayscalendar(self._date.year, self._date.month)
        for week in month:
            for index in range(CalendarPop.DAYS_A_WEEK):
                if week[index] != 0:
                    row = month.index(week)+2
                    date = week[index]
                    button = tkinter.Button(self, text=date, width=2, command=lambda x=date: self.button_pressed(x))
                    button.grid(row=row, column=index)
                    self.day_buttons.append(button)
        self.month_var.set(self._date.strftime('%B %Y'))

    def _prev_month(self):
        temp_date = self._date - datetime.timedelta(days=1)
        self._date = datetime.date(temp_date.year, temp_date.month, 1)
        self._update_calendar()

    def _next_month(self):
        temp_date = self._date + datetime.timedelta(days=31)
        self._date = datetime.date(temp_date.year, temp_date.month, 1)
        self._update_calendar()

    def button_pressed(self, day):
        self.variable.set(datetime.date(self._date.year, self._date.month, day).strftime('%Y-%m-%d'))
        self.master.destroy()


class ConfigurationSettings(ttk.Frame):

    class SaveSettings:
        def __init__(self, save):
            self.port_tv = None
            self.quick_tv = None
            self.shift_tv = None
            self.machine_ports = None
            self.quick_access = None
            self.shift_settings = None
            self.request_time = tkinter.IntVar()
            self.file_path = tkinter.StringVar()
            self.get_copies(save)

        def get_copies(self, save: serverDB.ServerSettings):
            self.machine_ports = save.machine_ports.copy()
            self.quick_access = save.quick_access.copy()
            self.shift_settings = save.shift_settings.copy()
            misc_settings = save.misc_settings.copy()
            self.request_time.set(misc_settings[save.REQUEST_TIME])
            self.file_path.set(misc_settings[save.FILE_PATH])

    def __init__(self, parent, save: serverDB.ServerSettings, database: serverDB.DatabaseManager, request_interval,
                 being=None, **kwargs):
        ttk.Frame.__init__(self, parent, **kwargs)
        self.being = being
        self.master.protocol('WM_DELETE_WINDOW', self.quit_parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.configuration_notebook = ttk.Notebook(self)
        self.configuration_notebook.grid(row=0, column=0, sticky='nsew')
        self.button_frame = ttk.Frame(self)
        self.button_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        save_button = ttk.Button(self.button_frame, text='Save', command=self.save_configuration_settings)
        save_button.pack(side=tkinter.RIGHT)
        cancel_button = ttk.Button(self.button_frame, text='Cancel', command=self.quit_parent)
        cancel_button.pack(side=tkinter.RIGHT)
        self.to_save = ConfigurationSettings.SaveSettings(save)
        self.save = save
        self.database = database
        self.request_interval = request_interval
        self.port_network_setup()
        self.quick_access_setup()
        self.shift_setup()
        self.miscellaneous_setup()

        self.grab_set()

    def port_network_setup(self):  # Port Settings
        port_config_frame = ttk.Frame(self.configuration_notebook)
        self.configuration_notebook.add(port_config_frame, text='Network Ports')
        port_config_frame.columnconfigure(0, weight=5)
        port_config_frame.columnconfigure(1, weight=1)
        port_config_frame.rowconfigure(0, weight=1)
        # Port Settings TreeView
        port_tv_frame = ttk.Frame(port_config_frame)
        port_tv_frame.grid(row=0, column=0, sticky='nsew')
        port_tv_frame.rowconfigure(0, weight=1)
        port_tv_frame.columnconfigure(0, weight=1)
        self.to_save.port_tv = ttk.Treeview(port_tv_frame)
        self.to_save.port_tv.grid(row=0, column=0, sticky='nsew')
        self.to_save.port_tv['show'] = 'headings'
        self.to_save.port_tv['column'] = ('machine', 'address', 'port')
        self.to_save.port_tv.heading('machine', text='Machine')
        self.to_save.port_tv.heading('address', text='Address')
        self.to_save.port_tv.heading('port', text='Port')
        self.to_save.port_tv.column('machine', width=200)
        self.to_save.port_tv.column('address', width=100, anchor=tkinter.E)
        self.to_save.port_tv.column('port', width=20, anchor=tkinter.E)
        # Scroll for Treeview
        port_tv_v_scroll = ttk.Scrollbar(port_tv_frame, orient='vertical', command=self.to_save.port_tv.yview)
        port_tv_v_scroll.grid(row=0, column=1, sticky='nsw')
        self.to_save.port_tv.configure(yscrollcommand=port_tv_v_scroll.set)
        # Populate port_tv
        for machine, (address, port) in self.to_save.machine_ports.items():
            self.to_save.port_tv.insert('', tkinter.END, values=(machine, address, port), tag=('move', ))
        # Add & Delete buttons
        button_frame = ttk.Frame(port_config_frame)
        button_frame.grid(row=0, column=2, padx=5, pady=5)
        add_button = ttk.Button(button_frame, text='Add', command=self.launch_network_port_window)
        add_button.pack(side=tkinter.TOP)
        edit_button = ttk.Button(button_frame, text='Edit', command=lambda: self.launch_network_port_window(edit=True))
        edit_button.pack(side=tkinter.TOP)
        delete_button = ttk.Button(button_frame, text='Delete', command=lambda: self.delete_treeview_item(
            self.to_save.port_tv))
        delete_button.pack(side=tkinter.TOP)

        up_button = ttk.Button(button_frame, text='\u25B2', command=lambda: self.move_item(self.to_save.port_tv, -1))
        up_button.pack(side=tkinter.TOP, pady=(20, 0))
        down_button = ttk.Button(button_frame, text='\u25BC', command=lambda: self.move_item(self.to_save.port_tv, 1))
        down_button.pack(side=tkinter.TOP)

    def quick_access_setup(self):  # Quick Access
        quick_access_frame = ttk.Frame(self.configuration_notebook)
        self.configuration_notebook.add(quick_access_frame, text='Quick Access')
        quick_access_frame.columnconfigure(0, weight=5)
        quick_access_frame.columnconfigure(1, weight=1)
        quick_access_frame.rowconfigure(0, weight=1)
        # Quick Access TreeView
        quick_tv_frame = ttk.Frame(quick_access_frame)
        quick_tv_frame.grid(row=0, column=0, sticky='nsew')
        quick_tv_frame.rowconfigure(0, weight=1)
        quick_tv_frame.columnconfigure(0, weight=1)
        self.to_save.quick_tv = ttk.Treeview(quick_tv_frame)
        self.to_save.quick_tv.grid(row=0, column=0, sticky='nsew')
        # Scroll for Treeview
        quick_tv_v_scroll = ttk.Scrollbar(quick_tv_frame, orient='vertical', command=self.to_save.quick_tv.yview)
        quick_tv_v_scroll.grid(row=0, column=1, sticky='nsw')
        self.to_save.quick_tv.configure(yscrollcommand=quick_tv_v_scroll.set)
        self.to_save.quick_tv['column'] = ('mode', 'detail')
        self.to_save.quick_tv.heading('#0', text='Machine')
        self.to_save.quick_tv.heading('mode', text='Mode')
        self.to_save.quick_tv.heading('detail', text='Details')
        self.to_save.quick_tv.column('#0', width=150)
        self.to_save.quick_tv.column('mode', width=50)
        self.to_save.quick_tv.column('detail', width=200)
        # Populate quick_tv here
        for key, setting_list in self.to_save.quick_access.items():
            iid = self.to_save.quick_tv.insert('', tkinter.END, text=key, tag=('top', 'move'), open=True)
            for graph, (machine_list, mode, detail) in setting_list.items():
                details = ' \u27A1 '.join(detail)
                _iid = self.to_save.quick_tv.insert(iid, tkinter.END, text=graph, values=(mode, details),
                                                    tag=('move', ))
                for machine in machine_list:
                    self.to_save.quick_tv.insert(_iid, tkinter.END, text=machine)

        self.to_save.quick_tv.tag_configure('top', font=('Helvetica', 15, 'bold'))
        # Add & Delete buttons
        button_frame = ttk.Frame(quick_access_frame)
        button_frame.grid(row=0, column=1, padx=5, pady=5)
        add_button = ttk.Button(button_frame, text='Add', command=self.add_quick_access)
        add_button.pack()
        delete_button = ttk.Button(button_frame, text='Delete', command=lambda: self.delete_treeview_item(
            self.to_save.quick_tv))
        delete_button.pack()

        up_button = ttk.Button(button_frame, text='\u25B2', command=lambda: self.move_item(self.to_save.quick_tv, -1))
        up_button.pack(side=tkinter.TOP, pady=(20, 0))
        down_button = ttk.Button(button_frame, text='\u25BC', command=lambda: self.move_item(self.to_save.quick_tv, 1))
        down_button.pack(side=tkinter.TOP)

    def shift_setup(self):  # Shift settings
        shift_frame = ttk.Frame(self.configuration_notebook)
        self.configuration_notebook.add(shift_frame, text='Shift')
        shift_frame.columnconfigure(0, weight=5)
        shift_frame.columnconfigure(1, weight=1)
        shift_frame.rowconfigure(0, weight=1)
        # Shift TreeView
        shift_tv_frame = ttk.Frame(shift_frame)
        shift_tv_frame.grid(row=0, column=0, sticky='nsew')
        shift_tv_frame.rowconfigure(0, weight=1)
        shift_tv_frame.columnconfigure(0, weight=1)
        self.to_save.shift_tv = ttk.Treeview(shift_tv_frame)
        self.to_save.shift_tv.grid(row=0, column=0, sticky='nsew')
        self.to_save.shift_tv['show'] = 'headings'
        self.to_save.shift_tv['column'] = ('shift', 'start', 'end')
        self.to_save.shift_tv.heading('shift', text='Shift')
        self.to_save.shift_tv.heading('start', text='Start Time')
        self.to_save.shift_tv.heading('end', text='End Time')
        self.to_save.shift_tv.column('shift', width=200)
        self.to_save.shift_tv.column('start', width=20)
        self.to_save.shift_tv.column('end', width=20)
        # Scroll for Treeview
        shift_tv_v_scroll = ttk.Scrollbar(shift_tv_frame, orient='vertical', command=self.to_save.shift_tv.yview)
        shift_tv_v_scroll.grid(row=0, column=1, sticky='nsw')
        self.to_save.shift_tv.configure(yscrollcommand=shift_tv_v_scroll.set)
        # Populate treeview
        for name, (start, duration) in self.to_save.shift_settings.items():
            start_date = datetime.datetime.strptime(start, '%H:%M')
            end_date = self.save.get_end_time(start_date, duration)
            end = end_date.strftime('%H:%M')
            self.to_save.shift_tv.insert('', tkinter.END, values=(name, start, end), tag=('move', ))

        # Add/Delete Button Frame
        button_frame = ttk.Frame(shift_frame)
        button_frame.grid(row=0, column=1, padx=5, pady=5)
        add_button = ttk.Button(button_frame, text='Add', command=self.add_shift)
        add_button.pack()
        del_button = ttk.Button(button_frame, text='Delete', command=lambda: self.delete_treeview_item(
            self.to_save.shift_tv))
        del_button.pack()

        up_button = ttk.Button(button_frame, text='\u25B2', command=lambda: self.move_item(self.to_save.shift_tv, -1))
        up_button.pack(side=tkinter.TOP, pady=(20, 0))
        down_button = ttk.Button(button_frame, text='\u25BC', command=lambda: self.move_item(self.to_save.shift_tv, 1))
        down_button.pack(side=tkinter.TOP)

    def miscellaneous_setup(self):  # Miscellaneous
        # Create Frame
        misc_frame = ttk.Frame(self.configuration_notebook)
        self.configuration_notebook.add(misc_frame, text='Miscellaneous')
        # Add label & OptionMenu for Request
        request_label = ttk.Label(misc_frame, text='Request interval: ')
        request_label.grid(row=0, column=0, sticky='e')
        request_list = (5, 10, 15, 20, 30)
        minute = int(self.request_interval.get().split()[2])
        self.to_save.request_time.set(minute)
        request_option = ttk.OptionMenu(misc_frame, self.to_save.request_time, self.to_save.request_time.get(),
                                        *request_list)
        request_option.grid(row=0, column=1, sticky='w')
        # Add location to save the databases
        location_label = ttk.Label(misc_frame, text='Database location: ')
        location_label.grid(row=1, column=0, sticky='e')
        location_entry = ttk.Entry(misc_frame, textvariable=self.to_save.file_path, state=tkinter.DISABLED, width=40)
        location_entry.grid(row=1, column=1, sticky='w')
        dir_browser = ttk.Button(misc_frame, text=u'\u2026', command=self.launch_file_dir)
        dir_browser.grid(row=1, column=2)

    def launch_file_dir(self):
        path = filedialog.askdirectory()
        self.to_save.file_path.set(path)

    def launch_network_port_window(self, edit=False):
        iid = self.to_save.port_tv.focus()
        if edit and iid == '':
            return
        network_port_window = tkinter.Toplevel(self)
        network_port_window.resizable(True, False)

        network_port_frame = AddNetworkPort(network_port_window, self.to_save.port_tv, iid)
        network_port_frame.pack(fill=tkinter.BOTH, expand=tkinter.TRUE)
        network_port_window.grab_set()

    def add_shift(self):
        if len(self.to_save.shift_tv.get_children()) >= ShiftSettings.MAX:
            messagebox.showinfo(title='Max', message='Maximum number of shifts is {}'.format(ShiftSettings.MAX))
            return
        shift_window = tkinter.Toplevel(self)
        shift_window.title('Add to Quick Access')
        shift_window.resizable(False, False)

        shift_frame = ShiftSettings(shift_window, self.to_save.shift_tv)
        shift_frame.pack(fill=tkinter.BOTH, expand=tkinter.TRUE)
        shift_frame.grab_set()

    def add_quick_access(self):
        detail_settings_window = tkinter.Toplevel(self)
        detail_settings_window.resizable(False, False)

        detail_frame = GraphDetailSettingsPage(detail_settings_window, self.save, self.database,
                                               quick_tv=self.to_save.quick_tv)
        detail_frame.pack(fill=tkinter.BOTH, expand=tkinter.TRUE)
        detail_frame.grab_set()

    @staticmethod
    def move_item(treeview: ttk.Treeview, direction):
        item = treeview.focus()
        if item != '' and treeview.tag_has('move', item):
            index = treeview.index(item) + direction
            treeview.move(item, treeview.parent(item), index)

    def save_configuration_settings(self):
        self.to_save.machine_ports.clear()
        for iid in self.to_save.port_tv.get_children():
            machine, address, port = self.to_save.port_tv.item(iid)['values']
            self.to_save.machine_ports[machine] = (address, port)

        self.to_save.quick_access.clear()
        for iid in self.to_save.quick_tv.get_children():
            button_name = self.to_save.quick_tv.item(iid)['text']
            graphs_list = {}
            for graph_iid in self.to_save.quick_tv.get_children(iid):
                graph = self.to_save.quick_tv.item(graph_iid)['text']
                mode, detail = self.to_save.quick_tv.item(graph_iid)['values']
                detail = detail.split(' \u27A1 ')
                detail1 = detail[0]
                detail2 = detail[1]
                machine_list = []
                for _iid in self.to_save.quick_tv.get_children(graph_iid):
                    machine_list.append(self.to_save.quick_tv.item(_iid)['text'])

                graphs_list[graph] = (machine_list, mode, (detail1, detail2))
            self.to_save.quick_access[button_name] = graphs_list

        self.to_save.shift_settings.clear()
        for iid in self.to_save.shift_tv.get_children():
            name, start, end = self.to_save.shift_tv.item(iid)['values']
            duration = self.save.convert_to_duration(start, end)
            self.to_save.shift_settings[name] = (start, duration.total_seconds())

        misc_temp = {self.save.REQUEST_TIME: self.to_save.request_time.get(),
                     self.save.FILE_PATH: self.to_save.file_path.get()}

        self.save.machine_ports = self.to_save.machine_ports
        self.save.quick_access = self.to_save.quick_access
        self.save.shift_settings = self.to_save.shift_settings
        self.save.misc_settings = misc_temp
        self.save.save_settings()
        self.quit_parent()
        self.request_interval.set('Requesting every {} minutes'.format(self.to_save.request_time.get()))
        # TODO reset apscheduler for job
        self.master.master.quick_access_setup()

    def quit_parent(self):
        self.master.destroy()
        if self.being:
            self.being = None

    @staticmethod
    def validate_time(values, new):
        if len(values) < 6:
            return new.isdigit() or (new == ':')
        else:
            return False

    @staticmethod
    def delete_treeview_item(treeview: ttk.Treeview):
        iid = treeview.focus()
        if iid == '':
            return
        elif treeview.parent(iid) == '':
            treeview.delete(iid)
        elif len(treeview.get_children(treeview.parent(iid))) > 1:
            treeview.delete(iid)
        else:
            messagebox.showerror(title='Unable to delete', message='Minimum 1 plot/graph required')


class ShiftSettings(ttk.Frame):
    LABEL_NAMES = ('Name: ', 'Start time: ', 'End time: ')
    MAX = 7

    def __init__(self, parent, treeview: ttk.Treeview):
        ttk.Frame.__init__(self, parent)
        self.treeview = treeview
        self.grid(row=0, column=0, sticky='nsew')
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        for index in range(len(ShiftSettings.LABEL_NAMES)):
            label = ttk.Label(self, text=ShiftSettings.LABEL_NAMES[index], width=11)
            label.grid(row=index, column=0, sticky='w', padx=5, pady=5)
        # Entries
        entry_validation = self.register(ShiftSettings.validate_dates)
        self.name_entry = ttk.Entry(self)
        self.name_entry.grid(row=0, column=1, sticky='w')
        self.name_entry.focus_set()
        self.start_entry = ttk.Entry(self, width=6, validate='key',
                                     validatecommand=(entry_validation, '%P', '%S'))
        self.start_entry.grid(row=1, column=1, sticky='w')
        self.end_entry = ttk.Entry(self, width=6, validate='key',
                                   validatecommand=(entry_validation, '%P', '%S'))
        self.end_entry.grid(row=2, column=1, sticky='w')
        # Add button
        add_button = ttk.Button(self, text='Add', command=self.add_shift)
        add_button.grid(row=3, column=1, sticky='e')

    def add_shift(self):
        msg = self.add_validation()
        if msg is True:
            self.treeview.insert('', tkinter.END, values=(self.name_entry.get(), self.start_entry.get(),
                                                          self.end_entry.get()))
            self.quit_parent()
        else:
            messagebox.showerror(title='Error', message=msg)

    def add_validation(self):
        messages = []
        name = self.name_entry.get()
        if len(name) < 1:
            messages.append('Please enter a name')
        start = self.start_entry.get()
        if len(start) < 1:
            messages.append('Please enter a start time')
        else:
            try:
                datetime.datetime.strptime(start, '%H:%M')
            except ValueError:
                messages.append('Incorrect time format, HH:MM')

        end = self.end_entry.get()
        if len(end) < 1:
            messages.append('Please enter an end time')
        else:
            try:
                datetime.datetime.strptime(end, '%H:%M')
            except ValueError:
                messages.append('Incorrect time format, HH:MM')

        for item in self.treeview.get_children():
            c_name, c_start, c_end = self.treeview.item(item)['values']
            if c_name == name:
                messages.append('Duplicated Name found')

        if messages:
            return '\n'.join(messages)
        else:
            return True

    def quit_parent(self):
        self.master.destroy()

    @staticmethod
    def validate_dates(values, new):
        if len(values) < 6:
            return new.isdigit() or (new == ':')
        else:
            return False


class AddNetworkPort(ttk.Frame):

    def __init__(self, parent, treeview: ttk.Treeview, _iid=''):
        ttk.Frame.__init__(self, parent)
        self.iid = _iid
        self.treeview = treeview
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        # Labels
        machine_label = ttk.Label(self, text='Name')
        machine_label.grid(row=0, column=0, sticky='e')
        address_label = ttk.Label(self, text='Network Address')
        address_label.grid(row=1, column=0, sticky='e')
        port_label = ttk.Label(self, text='Port')
        port_label.grid(row=2, column=0, sticky='e')
        # Entries
        entry_validation = self.register(AddNetworkPort.validate_entries)
        self.machine_entry = ttk.Entry(self, validate='key',
                                       validatecommand=(entry_validation, '%P', '%S', 'name'))
        self.machine_entry.delete(0, tkinter.END)
        self.machine_entry.grid(row=0, column=1, sticky='w')
        self.machine_entry.focus_set()
        self.address_entry = ttk.Entry(self, justify=tkinter.RIGHT, width=17,
                                       validate='key', validatecommand=(entry_validation, '%P', '%S', 'address'))
        self.address_entry.delete(0, tkinter.END)
        self.address_entry.grid(row=1, column=1, sticky='w')
        self.port_entry = ttk.Entry(self, justify=tkinter.RIGHT, width=6,
                                    validate='key', validatecommand=(entry_validation, '%P', '%S', 'port'))
        self.port_entry.delete(0, tkinter.END)
        self.port_entry.grid(row=2, column=1, sticky='w')

        # Button Frame
        button_frame = ttk.Frame(self)
        button_frame.grid(row=3, column=0, columnspan=2, sticky='nsew', padx=5, pady=5)
        save_button = ttk.Button(button_frame, text='Save', command=self.save_clicked)
        save_button.pack(side=tkinter.RIGHT)
        cancel_button = ttk.Button(button_frame, text='Cancel', command=self.master.destroy)
        cancel_button.pack(side=tkinter.RIGHT)

        if self.iid != '':
            name, address, port = self.treeview.item(self.iid)['values']
            self.machine_entry.insert(0, name)
            for num in [x for x in address.split('.')]:
                self.address_entry.insert(tkinter.END, num)
                self.address_entry.insert(tkinter.END, '.')
            self.address_entry.delete(len(self.address_entry.get()) - 1)
            self.port_entry.insert(0, port)

    def validate_before_save(self):
        if self.iid:
            name, address, port = self.treeview.item(self.iid)['values']
            if self.address_entry.get() != name:
                result = messagebox.askokcancel(title='Warning', message='Will not be able to retrieve pass data once '
                                                                         'name is changed.\nProceed?', icon='warning')
                if result is False:
                    return
        messages = []
        if len(self.machine_entry.get()) < 1:
            messages.append('Please enter a name')
        address = self.address_entry.get()
        if len(address) < 1:
            messages.append('Please enter a network address.')
        else:
            try:
                address_list = [int(x) for x in address.split('.')]
                if len(address_list) == 4:
                    if not max(address_list) < 256:
                        messages.append('Incorrect Network address format.')
                else:
                    messages.append('Incorrect Network address format.')
            except ValueError:
                messages.append('Incorrect Network address format.')

        if len(self.port_entry.get()) < 1:
            messages.append('Please enter a port')

        for _iid in self.treeview.get_children():
            if _iid != self.iid:
                c_name, c_address, c_port = self.treeview.item(_iid)['values']
                if c_name == self.machine_entry.get():
                    messages.append('Duplicate ID Found')
                if c_address == self.address_entry.get():
                    messages.append('Duplicate Address Found')

        if messages:
            return '\n'.join(messages)
        else:
            return True

    def save_clicked(self):
        msg = self.validate_before_save()
        if msg is True:
            if self.iid == '':
                self.treeview.insert('', tkinter.END, values=(self.machine_entry.get(), self.address_entry.get(),
                                                              self.port_entry.get()))
            else:
                self.treeview.item(self.iid, values=(self.machine_entry.get(), self.address_entry.get(),
                                                     self.port_entry.get()))
            self.quit_parent()
        else:
            messagebox.showerror('Error', msg)

    def quit_parent(self):
        self.master.destroy()

    @staticmethod
    def validate_entries(values, new, widget):
        if widget == 'name':
            return new.isalnum()
        elif widget == 'address' and len(values) < 16:
            return new.isdigit() or new == '.'
        elif widget == 'port' and len(values) < 6:
            return new.isdigit()
        else:
            return False


if __name__ == '__main__':
    root = tkinter.Tk()
    root.title('afRPIsens Server')
    root.minsize(width=1000, height=400)
    main_frame = MainWindow(root, serverDB.ServerSettings())
    main_frame.pack(fill=tkinter.BOTH, expand=tkinter.TRUE)
    # root.mainloop()
    while True:
        try:
            root.mainloop()
        except UnicodeDecodeError:
            continue
        else:
            break
