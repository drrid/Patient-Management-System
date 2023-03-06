from textual.app import App
from textual.screen import Screen
from textual.widgets import Static, Footer, Header, Input, DataTable, Button
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual import events
import conf
import csv
import io
import numpy as np
import datetime as dt
import calendar
from dateutil import parser


# Custom Calendar DataTable ---------------------------------------------------------------------------------------------------------------------------------------------
class CalTable(DataTable):

    def watch_cursor_cell(self, old, value):
        self.screen.change_week(self.screen.inde)
        selected_cell = self.data[self.cursor_cell.row][self.cursor_cell.column]

        pt_table = self.screen.create_find_pt()
        enc_table = self.screen.create_find_enc()

        if '_' not in selected_cell:
            pt_id = int(selected_cell.split(' ')[-1])
            selected_pts_list = conf.select_one_id(pt_id)
            rows = csv.reader(io.StringIO(str(selected_pts_list)))
            pt_table.add_rows(rows)
            self.screen.show_encounters(pt_table.data[0][0])

        return super().watch_cursor_cell(old, value)

# Custom Patient DataTable ---------------------------------------------------------------------------------------------------------------------------------------------
class PatientTable(DataTable):

    def watch_cursor_cell(self, old, value):
        self.screen.change_week(self.screen.inde)
        pt_id = self.data[self.cursor_cell.row][0]
        enc_table = self.screen.create_find_enc()
        self.screen.show_encounters(pt_id)

        return super().watch_cursor_cell(old, value)

# Custom Encounter DataTable ---------------------------------------------------------------------------------------------------------------------------------------------
class EncounterTable(DataTable):

    def watch_cursor_cell(self, old, value):
        self.screen.change_week(self.screen.inde)
        enc_notes = self.data[self.cursor_cell.row][2]
        self.screen.query_one('#notes').value = enc_notes
        self.screen.query_one('#notes').focus()
        return super().watch_cursor_cell(old, value)


# Calendar Screen --------------------------------------------------------------------------------------------------------------------------------------------------
class Calendar(Screen):
    BINDINGS = [("f1", "switch_screen('screen1')", "Calendar"), 
        ("f2", "switch_screen('screen2')", "Add Patient"),
        ("f3", "switch_screen('screen3')", "Patient Dashboard")]
    inde = reactive(0)
    selected_value = reactive([])
    selected_value2 = reactive([])

    def compose(self):
        # yield Header()
        yield Footer()
        yield Container(
                Vertical(Vertical(Input('', placeholder='First Name', id='fname'),
                                Input('', placeholder='Last Name', id='lname'),
                                Input('', placeholder='Phone', id='phone'),
                                Input('', placeholder='Date Of Birth', id='dob'),
                                Button('Add', id='addpatient'), 
                                id='pt_add_cnt'),
                        Vertical(Input(placeholder='Fee', classes='left_btm'), 
                                Button('Update', id='updatefee',classes='left_btm_btn'),
                                Input(placeholder='Payment', classes='left_btm'), 
                                Button('Add', id='addpayment',classes='left_btm_btn'), 
                                id='payments_cnt'), 
                        id='left_cnt'),
                Vertical(Horizontal(PatientTable(fixed_columns=1, zebra_stripes=True, id='pt_table'),
                                EncounterTable(fixed_columns=1, zebra_stripes=True, id='enc_table'),
                                Input(placeholder='Notes...', id='notes'),
                                id='upper_cnt'),
                        DataTable(fixed_columns=1, zebra_stripes=True, id='feedback_table'),
                        CalTable(fixed_columns=1, zebra_stripes=True, id='cal_table'),
                        id='right_cnt'),
                id='app_grid')
    

    def on_mount(self):

        self.change_week(self.inde)
        self.create_find_pt()
        self.search_patient()
        self.create_find_enc()
    

    def on_input_changed(self, event: Input.Changed):
        if event.sender.id in ['fname', 'lname', 'phone']:
            self.search_patient()


    def search_patient(self):
        table = self.create_find_pt()
        fname = self.query_one('#fname').value
        lname = self.query_one('#lname').value
        phone = self.query_one('#phone').value
        
        if phone.isdigit():
            phone = int(phone)
        else:
            self.query_one('#phone').value = ''

        selected_pts_list = conf.select_all_starts_with_all_fields(fname, lname, phone)
        if selected_pts_list:
            selected_pts_list_str = "\n".join([str(r) for r in selected_pts_list])
            rows = csv.reader(io.StringIO(selected_pts_list_str))
            table.add_rows(rows)

        if len(selected_pts_list) == 1:
            self.show_encounters(table.data[0][0])


    def show_encounters(self, pt_id):
        if pt_id:
            enc_table = self.create_find_enc()
            selected_pts_list2 = conf.select_all_pt_encounters(int(pt_id))
            if selected_pts_list2:
                selected_pts_list_str2 = "\n".join([str(r) for r in selected_pts_list2])
                rows = csv.reader(io.StringIO(selected_pts_list_str2))
                enc_table.add_rows(rows)
    

    def on_input_submitted(self, event: Input.Submitted):
        # submit patient and return to calendar only if selected encounter and patient

        table = self.query_one('#pt_table')
        fname = self.query_one('#fname').value
        lname = self.query_one('#lname').value
        phone = self.query_one('#phone').value

        if event.sender.id == 'notes':
            enc_table = self.query_one('#enc_table')
            encounter_id = int(enc_table.data[enc_table.cursor_cell.row][0])
            note = self.query_one('#notes').value
            conf.update_note(encounter_id, note)
            self.show_encounters(table.data[table.cursor_cell.row][0])

        if event.sender.id in ['fname', 'lname', 'phone']:
            if fname == '' and lname == '' and phone == '':
                return
            if '_' not in self.selected_value:
                return
            if not self.selected_value:
                return
            if len(table.data) == 0:
                return
            if len(table.data) > 1:
                self.query_one('#pt_table').focus()
                return
            if len(table.data) == 1:
                self.selected_value2 = [0, 0, 0]
                self.submit_patient()


    def on_button_pressed(self, event: Button.Pressed):
        if event.sender.id == 'addpatient':
            fname = str(self.query_one('#fname', Input).value).capitalize()
            lname = str(self.query_one('#lname', Input).value).capitalize()
            phone = int(self.query_one('#phone', Input).value)
            date_of_birth = parser.parse(str(self.query_one('#dob', Input).value))

            # for input_widget in self.query(Input):
            #     input_widget.value = ''

            conf.save_to_db(conf.patient(first_name=fname, 
                            last_name=lname, 
                            phone=phone, 
                            date_of_birth=date_of_birth))

            self.search_patient()

    # show current, next or previous week
    def change_week(self, week):
        table = self.query_one('#cal_table')
        table.clear()
        table.columns = []
        start_date, end_date = conf.get_weekly_start_end(week)
        table.add_column('', width=7)
        DAYS = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednsday', 'Thursday', 'Friday']

        # render calendar columns
        for c, d in enumerate(DAYS):
            today = dt.datetime.today()
            today_midnight = dt.datetime(today.year, today.month, today.day, 0, 0)
            weekday = start_date + dt.timedelta(days=c)
            month = calendar.month_abbr[weekday.month]

            if weekday == today_midnight:
                table.add_column(f'[bold yellow]{d} {weekday.day} {month}', width=22)
            else:
                table.add_column(f'[blue]{d} {weekday.day} {month}', width=22)
        
        # render calendar rows
        encounters = conf.select_week_encounters(start_date, end_date)
        csv_rows = conf.get_weekly_encounters_csv(encounters)
        with io.StringIO(csv_rows) as input_file:
            rows = csv.reader(input_file)
            for ro in rows:
                table.add_row(*ro, height=2)


    def on_key(self, event: events.Key):
        if event.key == 'ctrl+left':
            # show previous week
            self.inde -= 1
            self.change_week(self.inde)

        if event.key == 'ctrl+right':
            # show next week
            self.inde += 1
            self.change_week(self.inde)
            
        if event.key == 'space':
            table = self.query_one('#cal_table')
            # select encounter
            if len(table.data[0]) > 5:
                selected_v = table.data[table.cursor_cell.row][table.cursor_cell.column]
                self.selected_value = [table.cursor_cell.row, table.cursor_cell.column, selected_v]
                if selected_v == '_':
                    self.create_find_pt()
                    for inp in self.query(Input):
                        inp.value = ''
                    self.query_one('#fname').focus()

            # select patient 
            else:
                selected_v2 = table.data[table.cursor_cell.row][table.cursor_cell.column]
                self.selected_value2 = [table.cursor_cell.row, table.cursor_cell.column, selected_v2]
                self.submit_patient()

    def create_find_pt(self):
        table = self.query_one('#pt_table')
        table.clear()
        table.columns = []
        PT_CLMN = ['ID', 'First Name', 'Last Name', 'Date of Birth', 'Phone']
        for c in PT_CLMN:
            table.add_column(f'{c}')
        return table

    def create_find_enc(self):
        table = self.query_one('#enc_table')
        table.clear()
        table.columns = []
        PT_CLMN = ['ID', 'Encounter', 'Note', 'Payment']
        for c in PT_CLMN:
            table.add_column(f'{c}')
        return table


    def submit_patient(self):
        if ('_' not in self.selected_value) or not self.selected_value:
            return
        
        table = self.query_one('#pt_table')
        selected_patient_id = table.data[self.selected_value2[0]][0]
        finaltime = self.calculate_rdvtime()
        pt_encounter = conf.Encounter(patient_id=selected_patient_id, rdv=finaltime)
        if not conf.select_encounter(pt_encounter):
            conf.save_to_db(pt_encounter)
            self.change_week(self.inde)
            self.show_encounters(table.data[0][0])


    # boilerplate code to calculate encounter from selected cell
    def calculate_rdvtime(self):

        INV_DICT_ROW = {0:'9:0',1:'9:30',2:'10:0',3:'10:30',
        4:'11:0',5:'11:30',6:'12:0',7:'12:30',
        8:'13:0',9:'13:30',10:'14:0',11:'14:30',
        12:'15:0',13:'15:30'}

        start_date, end_date = conf.get_weekly_start_end(self.inde)
        encounter_date = start_date + dt.timedelta(days=self.selected_value[1]-1)
        hour, minute = INV_DICT_ROW.get(self.selected_value[0]).split(':')
        return dt.datetime(encounter_date.year, encounter_date.month, encounter_date.day, int(hour), int(minute))
        

# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 
# ------------------------------------------------------------------------Main App-----------------------------------------------------------------------------------------
class PMSApp(App):
    CSS_PATH = 'test.css'
    BINDINGS = [("f1", "switch_screen('screen1')", "Calendar")]
    SCREENS = {"screen1": Calendar()}
    
    def on_mount(self):
        #self.dark = False
        self.push_screen(self.SCREENS.get('screen1'))


if __name__ == "__main__":
    app = PMSApp()
    app.run()
# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 
# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 