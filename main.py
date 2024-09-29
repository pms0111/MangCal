import logging
from datetime import datetime, timedelta
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.colorpicker import ColorPicker  # ColorPicker 모듈 임포트
from kivy.properties import NumericProperty, ListProperty  # ListProperty 임포트
from kivy.uix.popup import Popup
from supabase import Client
import supabase_helper

# 로그 설정 (INFO 레벨로 설정)
logging.basicConfig(level=logging.INFO)

# 해상도에 따른 비율 계산
base_width, base_height = 1280, 720  # 기본 해상도 값(예: Mac에서 테스트한 해상도)
scale_x = Window.width / base_width
scale_y = Window.height / base_height


class ColorPickerPopup(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color_picker = ColorPicker()
        self.color_picker.bind(color=self.on_color)  # 색상이 선택될 때 이벤트 바인딩
        self.add_widget(self.color_picker)

    def on_color(self, instance, value):
        # 선택한 색상을 적용할 메서드
        self.parent.parent.update_button_color(value)  # 부모에서 update_button_color 호출

class CalendarLayout(BoxLayout):
    year = NumericProperty(datetime.now().year)
    month = NumericProperty(datetime.now().month)
    day = NumericProperty(datetime.now().day)
    supabase_client: Client = None  # Supabase 클라이언트를 저장할 변수
    events = []  # 전체 일정 데이터를 저장할 리스트
    color_picker_popup = None # 팝업 인스턴스를 저장할 속성 추가
    selected_color = ListProperty([0.7, 0.7, 0.7, 1])  # 선택한 색상 저장, 초기값 설정

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.supabase_client = supabase_helper.create_supabase_client()  # Supabase 클라이언트 생성
        self.load_all_events()  # 전체 일정을 한 번에 불러옴
        self.update_calendar()
        self.color_popup = None  # 팝업을 저장할 속성 추가

    def load_all_events(self):
        """Supabase에서 전체 일정을 한 번에 가져와 저장"""
        response = supabase_helper.get_calendar_data(self.supabase_client)  # 전체 일정 가져오기
        self.events = response  # 전체 일정을 변수에 저장
        logging.info(f"전체 {len(self.events)}개 일정 로드")  # 전체 일정 로드 로그 출력

    def setGlobalColor(self):
        """글로벌 색상 선택 팝업을 열기 위한 메서드"""
        color_picker = ColorPicker()
        
        # 색상 선택기에서 색상 변경 시 호출되는 메서드
        color_picker.bind(color=self.on_color)

        # 팝업 객체 생성
        self.color_popup = Popup(title="색상 선택", content=color_picker, size_hint=(0.8, 0.8))
        
        # 팝업 열기
        self.color_popup.open()

    def on_color(self, instance, value):
        """선택된 색상을 모든 버튼에 적용하는 메서드"""
        self.selected_color = value  # 선택한 색상을 저장
        self.update_calendar()  # 색상 선택 후 즉시 업데이트
        # for btn in self.ids['calendar_grid'].children:
        #     btn.background_color = self.selected_color  # 저장된 색상으로 모든 버튼의 색상 변경

            



    def get_events_for_month(self, year, month):
        """특정 연도와 월에 해당하는 일정을 필터링"""
        month_start = datetime(year, month, 1)  # 해당 월의 1일
        next_month = (month_start + timedelta(days=32)).replace(day=1)  # 다음 달의 1일
        month_end = next_month - timedelta(days=1)  # 해당 월의 마지막 날

        # 해당 월의 일정만 필터링 (날짜 부분만 비교, 시간은 무시)
        filtered_events = [event for event in self.events if month_start <= datetime.strptime(event['schedule_day'][:10], "%Y-%m-%d") <= month_end]
        logging.info(f"{year}년 {month}월에 대한 {len(filtered_events)}개 일정 필터링")  # 필터링된 일정 로그 출력
        return filtered_events

    def update_calendar(self):
        # 수동으로 calendar_grid를 참조 (ids를 통해 kv 파일의 id로 연결)
        calendar_grid = self.ids['calendar_grid']
        calendar_grid.clear_widgets()

        # 요일 리스트 (일요일부터 토요일까지)
        weekdays = ['일', '월', '화', '수', '목', '금', '토']
        for weekday in weekdays:
            logging.info(f"요일 라벨 추가: {weekday}")  # 요일 라벨 추가 로그
            calendar_grid.add_widget(Label(text=weekday, bold=True, font_name="NanumGothic.ttf"))

        # 해당 월의 시작 날짜와 끝 날짜 계산
        first_day_of_month = datetime(self.year, self.month, 1)
        next_month = (first_day_of_month + timedelta(days=32)).replace(day=1)
        last_day_of_month = next_month - timedelta(days=1)

        # 이전 달의 마지막 날짜 계산
        previous_month = first_day_of_month - timedelta(days=1)
        previous_month_last_day = previous_month.day
        first_weekday = (first_day_of_month.weekday() + 1) % 7

        # 현재 월과 이전/다음 달의 일정 필터링
        current_month_events = self.get_events_for_month(self.year, self.month)
        previous_month_events = self.get_events_for_month(self.year if self.month > 1 else self.year - 1, 12 if self.month == 1 else self.month - 1)
        next_month_events = self.get_events_for_month(self.year if self.month < 12 else self.year + 1, 1 if self.month == 12 else self.month + 1)

        # 요일 맞추기 위해 이전 달의 날짜와 일정 채우기
        for day in range(first_weekday):
            prev_day = previous_month_last_day - first_weekday + day + 1
            date_str = f"{self.year if self.month > 1 else self.year - 1}-{12 if self.month == 1 else self.month - 1:02}-{prev_day:02}"
            day_events = [event for event in previous_month_events if event['schedule_day'][:10] == date_str]

            if day_events:
                event_texts = "\n\n".join([event['schedule_value'] for event in day_events])
                event_text = f"{prev_day}\n\n{event_texts}"
                logging.info(f"{date_str}에 대한 이전 달 일정 추가: {event_texts}")  # 일정 로그
            else:
                event_text = str(prev_day)
                logging.info(f"{date_str}에 이전 달 일정 없음")  # 일정 없음 로그

            # 이전 달 버튼 채도 낮춘 색상 적용
            darker_color = [c * 0.7 for c in self.selected_color[:3]] + [1]  # 채도를 낮춘 색상

            btn = Button(
                text=event_text,
                font_size='18',
                halign='left',
                valign='top',
                padding=(10, 10),
                font_name="NanumGothic.ttf",
                background_color=darker_color,  # 이전 달 일정은 채도가 낮아짐
                text_size=(self.width, None),
                on_press=lambda instance, m=self.month - 1: self.show_event_popup(instance, m))

            btn.bind(size=lambda instance, size: setattr(instance, 'text_size', size))
            calendar_grid.add_widget(btn)

        # 해당 월의 날짜와 일정 추가
        for day in range(1, last_day_of_month.day + 1):
            date_str = f"{self.year}-{self.month:02}-{day:02}"
            day_events = [event for event in current_month_events if event['schedule_day'][:10] == date_str]

            if day_events:
                event_texts = "\n\n".join([event['schedule_value'] for event in day_events])
                event_text = f"{day}\n\n{event_texts}"
                logging.info(f"{date_str}에 대한 일정 추가: {event_texts}")  # 일정 로그
            else:
                event_text = str(day)
                logging.info(f"{date_str}에 일정 없음")  # 일정 없음 로그

            btn = Button(
                text=str(day),
                font_size='18',
                halign='left',
                valign='top',
                padding=(10, 10),
                font_name="NanumGothic.ttf",
                background_color=self.selected_color,  # 저장된 색상으로 버튼 배경 설정
                text_size=(self.width, None),
                on_press=lambda instance, m=self.month: self.show_event_popup(instance, m)
            )
            btn.bind(size=lambda instance, size: setattr(instance, 'text_size', size))
            calendar_grid.add_widget(btn)

        # 다음 달의 날짜와 일정 추가
        total_days_displayed = first_weekday + last_day_of_month.day
        next_month_day = 1
        while total_days_displayed < 35:  # 7 * 5 그리드를 위해 총 35칸 필요
            date_str = f"{self.year if self.month < 12 else self.year + 1}-{1 if self.month == 12 else self.month + 1:02}-{next_month_day:02}"
            day_events = [event for event in next_month_events if event['schedule_day'][:10] == date_str]

            if day_events:
                event_texts = "\n\n".join([event['schedule_value'] for event in day_events])
                event_text = f"{next_month_day}\n\n{event_texts}"
                logging.info(f"{date_str}에 대한 다음 달 일정 추가: {event_texts}")  # 일정 로그
            else:
                event_text = str(next_month_day)
                logging.info(f"{date_str}에 다음 달 일정 없음")  # 일정 없음 로그

            # 다음 달 버튼 채도 낮춘 색상 적용
            darker_color = [c * 0.8 for c in self.selected_color[:3]] + [1]

            btn = Button(
                text=event_text,
                font_size='18',
                halign='left',
                valign='top',
                padding=(10, 10),
                font_name="NanumGothic.ttf",
                background_color=darker_color,  # 다음 달 일정 배경색
                text_size=(self.width, None),
                on_press=lambda instance, m=self.month + 1: self.show_event_popup(instance, m))

            btn.bind(size=lambda instance, size: setattr(instance, 'text_size', size))
            calendar_grid.add_widget(btn)

            next_month_day += 1
            total_days_displayed += 1


    def show_event_popup(self, instance, month):
        # instance.text에서 일자 부분만 추출하여 두 글자까지 자름
        selected_day_str = instance.text.split("\n")[0][:2].strip()  # 버튼 텍스트의 첫 번째 줄만 두 글자로 자름
        selected_day = int(selected_day_str)  # int로 변환하여 날짜로 사용

        # 선택된 날짜를 기반으로 포맷
        selected_date = datetime(self.year, month, selected_day)
        formatted_date = selected_date.strftime("%Y-%m-%d")

        logging.info(formatted_date)

        # 팝업 내용 설정
        popup_content = EventPopup()
        popup_content.ids.date_label.text = f"선택한 날짜: {formatted_date}"

        # 팝업 객체 생성 및 팝업을 content에 설정
        popup = Popup(title="", content=popup_content, size_hint=(0.8, 0.6))

        # 팝업 객체를 EventPopup에 전달
        popup_content.set_popup(popup)

        # 팝업 열기
        popup.open()

    def go_to_next_month(self):
        """다음 달로 이동"""
        if self.month == 12:
            self.month = 1
            self.year += 1
        else:
            self.month += 1
        logging.info(f"다음 달로 이동: {self.year}-{self.month}")  # 다음 달 이동 로그
        self.update_calendar()

    def go_to_previous_month(self):
        """이전 달로 이동"""
        if self.month == 1:
            self.month = 12
            self.year -= 1
        else:
            self.month -= 1
        logging.info(f"이전 달로 이동: {self.year}-{self.month}")  # 이전 달 이동 로그
        self.update_calendar()

class EventPopup(BoxLayout):
    popup = None  # Popup 객체를 저장할 속성

    def set_popup(self, popup_instance):
        """Popup 객체를 저장"""
        self.popup = popup_instance

    def submit_event(self, title, content):
        print(f"일정 제목: {title}, 내용: {content}")
        if self.popup:
            self.popup.dismiss()  # 팝업 창 닫기

class CalendarApp(App):
    def build(self):
        return CalendarLayout()

if __name__ == '__main__':
    CalendarApp().run()
