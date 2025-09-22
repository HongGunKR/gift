import streamlit as st

# data_fetcher.py : 주식 시장 데이터를 가져오는 함수들을 모아놓은 모듈
import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta
from duckduckgo_search import DDGS

def get_market_indices():
    """
    pykrx 라이브러리를 사용하여 KOSPI와 KOSDAQ의 최근 한 달간 지수 정보를 가져옵니다.
    
    Returns:
        DataFrame: 'KOSPI'와 'KOSDAQ' 지수 정보를 담은 pandas DataFrame.
                   인덱스는 날짜(Date)이며, 각 컬럼은 해당 지수의 종가(Close)입니다.
    """
    today = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

    kospi_df = stock.get_index_ohlcv_by_date(start_date, today, "1001")
    kosdaq_df = stock.get_index_ohlcv_by_date(start_date, today, "2001")

    indices_df = pd.concat([kospi_df['종가'].to_frame('KOSPI'), 
                            kosdaq_df['종가'].to_frame('KOSDAQ')], axis=1)
    
    indices_df.index = indices_df.index.strftime('%Y-%m-%d')
    
    return indices_df

def get_top_100_market_cap_stocks():
    """
    가장 최근 영업일 기준으로 시가총액 상위 100개 종목 정보를 조회합니다.
    (데이터 소스를 변경하여 안정성을 높인 최종 버전)
    
    Returns:
        DataFrame: 시가총액 상위 100개 종목의 최종 정보.
    """
    # 1. 가장 최근 영업일을 가져옵니다.
    latest_day = stock.get_nearest_business_day_in_a_week()
    
    # 2. 시가총액과 종가 정보를 가져옵니다. (출처 1)
    df_cap = stock.get_market_cap_by_ticker(latest_day)
    
    # 3. 종목명과 등락률 정보를 가져옵니다. (출처 2)
    # 이 함수가 '종목명'과 '등락률'을 가장 확실하게 제공합니다.
    df_change = stock.get_market_price_change_by_ticker(latest_day, latest_day)

    # 데이터 로딩에 실패한 경우, 빈 DataFrame을 반환합니다.
    if df_cap.empty or df_change.empty:
        return pd.DataFrame()

    # 4. 두 데이터를 '티커(종목코드)'를 기준으로 합칩니다.
    # df_change에서 '종목명'과 '등락률' 컬럼을 가져와 df_cap에 합칩니다.
    df_merged = pd.merge(df_cap, df_change[['종목명', '등락률']], left_index=True, right_index=True, how='left')

    # 5. 시가총액 순으로 정렬하고 상위 100개를 선택합니다.
    df_top100 = df_merged.sort_values(by='시가총액', ascending=False).head(100)
    
    # 6. 화면에 표시할 최종 컬럼들을 선택하고 순서를 정리합니다.
    df_final = df_top100[['종목명', '종가', '등락률', '시가총액']]
    
    # 7. 컬럼명을 변경하고 인덱스를 재설정합니다.
    df_final.rename(columns={'종목명': '이름', '종가': '현재가'}, inplace=True)
    df_final.reset_index(inplace=True)
    df_final.rename(columns={'티커': '종목코드'}, inplace=True)
    
    # 순위를 표시하기 위해 인덱스를 1부터 시작하도록 설정합니다.
    df_final.index = df_final.index + 1
    
    return df_final

# 종목명 <-> 종목코드 변환을 빠르게 하기 위해, 전체 목록을 캐싱해 둡니다.
# 앱 실행 시 한 번만 실행되어 효율성을 높입니다.
@st.cache_data(show_spinner=False)
def get_stock_name_ticker_map():
    """
    KOSPI와 KOSDAQ의 모든 종목에 대해 '종목명'을 Key, '종목코드'를 Value로 하는
    딕셔너리를 생성하여 반환합니다. (캐싱 사용)
    
    Returns:
        dict: {'삼성전자': '005930', 'SK하이닉스': '000660', ...}
    """
    tickers_kospi = stock.get_market_ticker_list(market="KOSPI")
    tickers_kosdaq = stock.get_market_ticker_list(market="KOSDAQ")
    all_tickers = tickers_kospi + tickers_kosdaq
    
    name_ticker_map = {stock.get_market_ticker_name(ticker): ticker for ticker in all_tickers}
    return name_ticker_map

def get_stock_info_by_name(stock_name):
    """
    종목명을 입력받아 해당 종목의 최근 1년간의 주가 정보(OHLCV)를 가져옵니다.
    
    Args:
        stock_name (str): 사용자가 입력한 종목명 (예: '삼성전자')
        
    Returns:
        DataFrame: 해당 종목의 1년간 OHLCV 데이터. 종목을 찾지 못하면 None 반환.
        str: 종목코드 (티커)
    """
    # 캐싱된 종목명-종목코드 맵을 가져옵니다.
    name_ticker_map = get_stock_name_ticker_map()
    
    # 입력된 종목명에 해당하는 종목코드를 찾습니다.
    ticker = name_ticker_map.get(stock_name)
    
    # 종목코드를 찾지 못하면 함수를 종료합니다.
    if ticker is None:
        return None, None
        
    # 1년 전 날짜를 계산합니다.
    today = datetime.now()
    start_date = (today - timedelta(days=365)).strftime('%Y%m%d')
    today_str = today.strftime('%Y%m%d')
    
    # 해당 종목의 1년간 주가 데이터를 조회합니다.
    df = stock.get_market_ohlcv_by_date(start_date, today_str, ticker)
    
    # 날짜 인덱스 형식을 'YYYY-MM-DD'로 변경합니다.
    df.index = df.index.strftime('%Y-%m-%d')
    
    return df, ticker

def search_stocks_by_keyword(keyword):
    """
    키워드(keyword)가 포함된 모든 종목명을 찾아 리스트로 반환합니다.
    
    Args:
        keyword (str): 사용자가 입력한 검색 키워드.
        
    Returns:
        list: 키워드를 포함하는 종목명들의 리스트. (예: ['삼성전자', '삼성바이오로직스'])
    """
    # 캐싱된 전체 종목명-종목코드 맵을 가져옵니다.
    name_ticker_map = get_stock_name_ticker_map()
    
    # 맵의 모든 종목명(key) 중에서 키워드를 포함하는 것들만 리스트로 만듭니다.
    matching_stocks = [name for name in name_ticker_map.keys() if keyword.lower() in name.lower()]
    
    return matching_stocks

def get_financial_ratios(ticker):
    """
    특정 종목(티커)의 최신 재무 지표를 조회합니다.
    
    Args:
        ticker (str): 종목코드
        
    Returns:
        dict: 주요 재무 지표(BPS, PER, PBR, EPS, DIV, DPS)를 담은 딕셔너리
    """
    # 가장 최근 영업일 기준으로 재무 정보를 조회합니다.
    latest_day = stock.get_nearest_business_day_in_a_week()
    
    # 해당 날짜의 재무 정보를 가져옵니다.
    df = stock.get_market_fundamental_by_ticker(latest_day)
    
    # 해당 티커의 재무 정보만 선택하여 딕셔너리로 변환합니다.
    ratios = df.loc[ticker].to_dict()
    
    return ratios

def search_news(stock_name):
    """
    특정 종목명으로 최신 뉴스 기사 5개를 검색하여 제목과 내용을 반환합니다.
    
    Args:
        stock_name (str): 검색할 종목명
        
    Returns:
        list of dict: 각 뉴스의 'title'과 'snippet'을 담은 딕셔너리 리스트
    """
    try:
        # DDGS를 사용하여 뉴스 검색
        with DDGS() as ddgs:
            # 한국 지역(kr-kr)에서 최신 뉴스(sort='date') 5개(max_results=5)를 검색
            results = list(ddgs.news(
                keywords=f"{stock_name} 주가",
                region="kr-kr",
                safesearch="off",
                timelimit="m", # 최근 한달
                max_results=5
            ))
        
        if not results:
            return None

        # 검색 결과에서 제목(title)과 본문 미리보기(body)만 추출
        news_list = [{"title": r['title'], "snippet": r['body']} for r in results]
        return news_list

    except Exception as e:
        print(f"뉴스 검색 중 오류 발생: {e}")
        return None