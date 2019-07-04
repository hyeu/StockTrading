import sys
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
import time
import sqlite3

TR_REQ_TIME_INTERVAL = 0.2

class Sig(QObject):
    sig = pyqtSignal()
    def __init__(self):
        super().__init__()
    def signal(self):
        self.sig.emit()

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self._create_kiwoom_instance()
        self._set_signal_slots()
        self.sig = Sig()
        self.orderNum = ""

    def signal_(self):
        self.sig.signal()

    # openAPI 사용을 위해선 COM 오브젝트 생성이 필요
    def _create_kiwoom_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    # 이벤트(signal)와 이를 처리할 메서드(slot) 연결
    def _set_signal_slots(self):
        self.OnEventConnect.connect(self._event_connect)
        self.OnReceiveTrData.connect(self._receive_tr_data)
        #self.OnReceiveRealData.connect(self._receive_real_data)
        self.OnReceiveChejanData.connect(self._receive_chejan_data)

    # 로그인 함수
    def comm_connect(self):
        # CommConnect 함수를 dynamicCall 함수를 통해 호출
        self.dynamicCall("CommConnect()")
        # 이벤트 루프(이벤트가 발생할 때까지 프로그램 종료되지 않음) / GUI형태로 만들지 않을 시 필요
        self.login_event_loop = QEventLoop()
        # exec_메서드를 호출하여 생성
        self.login_event_loop.exec_()

    # OnEventConnect 이벤트 발생 하면 _event_connect 호출
    # comm_connect 호출 시 생성된 이벤트 루프 종료
    def _event_connect(self, err_code):
        if err_code == 0:
            print('connected')
        else:
            print('disconnected')

        self.login_event_loop.exit()

    # 각 시장에 속하는 종목의 종목 코드 리스트 불러옴
    # 종목 코드는 ;로 구분
    def get_code_list_by_market(self, market):
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market)
        code_list = code_list.split(';')
        return code_list[:-1]

    # 종목 코드로부터 한글 종목명 얻어오기
    def get_master_code_name(self, code):
        code_name = self.dynamicCall("GetMasterCodeName(QString)", code)
        return code_name

    # 현재 접속 상태 반환
    def get_connect_state(self):
        ret = self.dynamicCall("GetConnectState()")
        return ret

    # 계좌 정보 및 로그인 사용자 정보 얻어오기
    def get_login_info(self, tag):
        ret = self.dynamicCall("GetLoginInfo(QString)", tag)
        return ret

    # TR 입력 값을 서버통신 전에 입력
    def set_input_value(self, id, value):
        self.dynamicCall("setInputValue(QString, QString)", id, value)

    # TR을 서버로 송신
    # 사용자 구분명, TR명, 조회:0/연속:2, 4개 화면번호
    # TR 처리 후 키움증권이 이벤트 줄 때까지 대기해야 하기 때문에 이벤트 루프 만들어줌
    def comm_rq_data(self, rqname, trcode, next, screen_no):
        self.dynamicCall("CommRqData(QString, QString, int, QString)", rqname, trcode, next, screen_no)
        self.tr_event_loop = QEventLoop()
        self.tr_event_loop.exec_()

    # TR 처리에 대한 이벤트가 발생했을 때 실제로 데이터 가져오기
    def _comm_get_data(self, code, real_type, field_name, index, item_name):
        ret = self.dynamicCall("CommGetData(QString, QString, QString, int, QString)", code,
                               real_type, field_name, index, item_name)
        return ret.strip()

        # 총 몇 개의 데이터가 왔는지 확인하기 위함
    def _get_repeat_cnt(self, trcode, rqname):
        ret = self.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
        return ret

    # 주식 주문에 대한 정보를 서버로 전송
    def send_order(self, rqname, screen_no, acc_no, order_type, code, quantity, price, hoga, order_no):
        self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                         [rqname, screen_no, acc_no, order_type, code, quantity, price, hoga, order_no])

    # 체결잔고 데이터 가져오기
    def get_chejan_data(self, fid):
        ret = self.dynamicCall("GetChejanData(int)", fid)
        return ret

    # 접속서버 구분
    def get_server_gubun(self):
        ret = self.dynamicCall("KOA_Functions(QString, QString)", "GetServerGubun", "")
        return ret

    # gubun: '0' 접수,체결 / '1' 잔고전달
    def _receive_chejan_data(self, gubun, item_cnt, fid_list):
        print(gubun)
        cj_jumooncode = self.get_chejan_data(9203)  # 주문번호
        cj_code = self.get_chejan_data(9001)  # 종목코드
        cj_name = self.get_chejan_data(302)  # 종목명
        cj_vol = self.get_chejan_data(900)  # 주문수량
        cj_wprice = self.get_chejan_data(901)  # 주문가격
        cj_time = self.get_chejan_data(908)  # 주문/체결 시간
        cj_actual_vol = self.get_chejan_data(911)  # 체결량
        cj_price = self.get_chejan_data(10)  # 현재가, 체결가, 실시간 종가

        cj_data = [cj_jumooncode, cj_code, cj_name, cj_vol, cj_wprice, cj_time, cj_actual_vol, cj_price]

        print(cj_data)
        return cj_data

    def _get_comm_real_data(self, code, fid):
        ret = self.dynamicCall("GetCommRealData(QString, int)", code, fid)
        return ret

    def _receive_real_data(self, scode, real_type, real_data):
        if real_type == '주식체결':
            self.scode = scode
            self.time = int(self.GetCommRealData(20))  # 체결시간
            self.price = int(self.GetCommRealData(10))  # 현재가
            if self.price < 0:
                self.price = self.price * (-1)
            self.vol = int(self.GetCommRealData(15))  # 거래량
            self.price_up_down = int(self.GetCommRealData(12))  # 등락률
            self.hour = self.time / 10000
            self.min = self.time / 100 % 100
            self.sec = self.time % 100
            self.realtime = self.hour * 3600 + self.min * 60 + self.sec
            self.code_name = self.get_master_code_name(scode)

            data = [self.realtime, scode, self.code_name, self.price, self.vol, self.price_up_down, self.realtime]
            print(data)
            return data

    # 실시간 등록
    def _set_real_reg(self, screen_no, code, fid_list, real_type):
        print("SetRealReg")
        self.dynamicCall("SetRealReg(QString, QString, QString, QString)",
                         screen_no, code, fid_list, real_type)

    # SetRealReg() 해제
    def _set_real_remove(self, screen_no, del_code):
        print("SetRealRemove")
        self.dynamicCall("SetRealRemove(QString, QString)", screen_no, del_code)

    def _on_receive_msg(self, screen_no, rqname, trcode, msg):
        msg = self.dynnamicCall("OnResceiveMsg(")

    # def _receive_real_condition(self, scode, event_type, condi_name, cond_index):
    # 이벤트 발생 시 처리
    def _receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2, unused3, unused4):
        self.orderNum = self._comm_get_data(trcode, "", rqname, 0, "주문번호")
        # next라는 인자 값을 통해 연속조회 필요여부
        if next == '2':
            self.remained_data = True
        else:
            self.remained_data = False

        # TR 구분을 위한 적당한 문자열
        # 올바른 데이터를 받기 위함
        if rqname == "opt10081_req":
            self._opt10081(rqname, trcode)
        # 예수금 정보
        elif rqname == "opw00001_req":
            self._opw00001(rqname, trcode)
        # 계좌 잔고 데이터
        elif rqname == "opw00018_req":
            self._opw00018(rqname, trcode)
        # 실시간 미체결 요청
        elif rqname == "opt10075_req":
            self._opt10075(rqname, trcode)

        # comm_rq_data 호출 시 생성된 이벤트 루프 종료
        try:
            self.tr_event_loop.exit()
        except AttributeError:
            pass

    # 숫자 정리. 콤마 표시
    @staticmethod
    def change_format(data):
        strip_data = data.lstrip('-0')
        if strip_data == '' or strip_data == '.00':
            strip_data = '0'

        format_data = format(int(strip_data), ',d')
        if data.startswith('-'):
            format_data = '-' + format_data

        return format_data

    @staticmethod
    def change_format2(data):
        strip_data = data.lstrip('-0')

        if strip_data == '':
            strip_data = '0'

        if strip_data.startswith('.'):
            strip_data = '0' + strip_data

        if data.startswith('-'):
            strip_data = '-' + strip_data

        return strip_data

    def reset_opt10075_output(self):
        self.opt10075_output = {'no_che': [], 'che': []}

    def _opt10075(self, rqname, trcode):
        data_cnt = self._get_repeat_cnt(trcode, rqname)
        for i in range(data_cnt):
            status = self._comm_get_data(trcode, "", rqname, i, "주문상태")
            gubun = self._comm_get_data(trcode, "", rqname, i, "주문구분")
            order_num = self._comm_get_data(trcode, "", rqname, i, "주문번호")
            code = self._comm_get_data(trcode, "", rqname, i, "종목명")
            price = self._comm_get_data(trcode, "", rqname, i, "체결가격")
            vol = self._comm_get_data(trcode, "", rqname, i, "주문수량")
            yet_vol = self._comm_get_data(trcode, "", rqname, i, "미체결수량")
            time = self._comm_get_data(trcode, "", rqname, i, "시간")

            # self.sig.signal()
            print(status, gubun, order_num, code, vol, yet_vol, time)
            self.opt10075_output['no_che'].append([status, gubun, order_num, code, vol, yet_vol, time])

    # 예수금 정보 얻기 위한 TR
    def _opw00001(self, rqname, trcode):
        d2_deposit = self._comm_get_data(trcode, "", rqname, 0, "d+2추정예수금")
        # 포맷 변경
        self.d2_deposit = Kiwoom.change_format(d2_deposit)

    def _opt10081(self, rqname, trcode):
        # 데이터를 얻어오기 전 데이터 개수 받아오기
        data_cnt = self._get_repeat_cnt(trcode, rqname)
        # 반복문을 통해 데이터 하나씩 얻어오기
        for i in range(data_cnt):
            date = self._comm_get_data(trcode, "", rqname, i, "일자")
            open = self._comm_get_data(trcode, "", rqname, i, "시가")
            high = self._comm_get_data(trcode, "", rqname, i, "고가")
            low = self._comm_get_data(trcode, "", rqname, i, "저가")
            close = self._comm_get_data(trcode, "", rqname, i, "현재가")
            volume = self._comm_get_data(trcode, "", rqname, i, "거래량")
            #time.sleep(0.2)

            self.ohlcv['date'].append(date)
            self.ohlcv['close'].append(int(close))

        print("날짜: ", self.ohlcv['date'][1])
        print("종가: ", self.ohlcv['close'][1])
        self.final['close'].append(self.ohlcv['close'][1])
        self.current['current'].append(self.ohlcv['close'][0])


    # 잔고 및 보유종목 현황
    def _opw00018(self, rqname, trcode):
        total_purchase_price = self._comm_get_data(trcode, "", rqname, 0, "총매입금액")
        total_eval_price = self._comm_get_data(trcode, "", rqname, 0, "총평가금액")
        total_eval_profit_loss_price = self._comm_get_data(trcode, "", rqname, 0, "총평가손익금액")
        total_earning_rate = self._comm_get_data(trcode, "", rqname, 0, "총수익률(%)")
        estimated_deposit = self._comm_get_data(trcode, "", rqname, 0, "추정예탁자산")

        self.opw00018_output['single'].append(Kiwoom.change_format(total_purchase_price))
        self.opw00018_output['single'].append(Kiwoom.change_format(total_eval_price))
        self.opw00018_output['single'].append(Kiwoom.change_format(total_eval_profit_loss_price))

        total_earning_rate = Kiwoom.change_format2(total_earning_rate)

        if self.get_server_gubun():
            total_earning_rate = float(total_earning_rate) / 100
            total_earning_rate = str(total_earning_rate)

        self.opw00018_output['single'].append(total_earning_rate)
        self.opw00018_output['single'].append(Kiwoom.change_format(estimated_deposit))


        #multi data
        rows = self._get_repeat_cnt(trcode, rqname)
        for i in range(rows):
            name = self._comm_get_data(trcode, "", rqname, i, "종목명")
            quantity = self._comm_get_data(trcode, "", rqname, i, "보유수량")
            purchase_price = self._comm_get_data(trcode, "", rqname, i, "매입가")
            current_price = self._comm_get_data(trcode, "", rqname, i, "현재가")
            eval_profit_loss_price = self._comm_get_data(trcode, "", rqname, i, "평가손익")
            earning_rate = self._comm_get_data(trcode, "", rqname, i, "수익률(%)")

            quantity = Kiwoom.change_format(quantity)
            purchase_price = Kiwoom.change_format(purchase_price)
            current_price = Kiwoom.change_format(current_price)
            eval_profit_loss_price = Kiwoom.change_format(eval_profit_loss_price)
            earning_rate = Kiwoom.change_format2(earning_rate)

            self.opw00018_output['multi'].append([name, quantity, purchase_price, current_price,
                                                  eval_profit_loss_price, earning_rate])
			self.opw00018_output['compare'].append([name, quantity, current_price, purchase_price, earning_rate])
    
    # opw00018 데이터 변수에 저장
    def reset_opw00018_output(self):
        self.opw00018_output = {'single': [], 'multi': [], 'compare': []}

    def store_fianl_close(self):
        self.final_close = []
        self.current_close = []


if __name__ == "__main__":
    app = QApplication(sys.argv)
    kiwoom = Kiwoom()
    kiwoom.comm_connect()
    # kiwoom.ohlcv = {'date' : [], 'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}

    kiwoom.reset_opw00018_output()
    account_number = kiwoom.get_login_info("ACCNO")
    account_number = account_number.split(';')[0]

    kiwoom.set_input_value("계좌번호", account_number)

    #kiwoom.comm_rq_data("opt10075_req", "opt10075", 0, "2000")