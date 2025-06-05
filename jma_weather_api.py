import requests
from datetime import datetime

def calculate_average_percentage(percentage_dict):
    """降水確率の平均を計算"""
    try:
        values = [float(value.replace('%', '')) for value in percentage_dict.values()]
        return sum(values) / len(values) if values else 0.0
    except (ValueError, AttributeError):
        return 0.0

def get_weather(day, city):
    try:
        url = f"https://weather.tsukumijima.net/api/forecast?city={city}"
        response = requests.get(url)
        response.raise_for_status()

        data_json = response.json()
    
        date_str = data_json["forecasts"][day]["date"]
        date = datetime.strptime(date_str,"%Y-%m-%d").strftime("%Y年%m月%d日")
        title = data_json["title"]
        weather = data_json["forecasts"][day]["telop"]
        max_temp = data_json["forecasts"][day]["temperature"]["max"]["celsius"]
        min_temp = data_json["forecasts"][day]["temperature"]["min"]["celsius"]
        chance_of_rain = data_json["forecasts"][day]["chanceOfRain"]
        chance_of_rain = {k: v for k, v in chance_of_rain.items() if v != "--%"}  # 空でない降水確率のみを抽出
        
        # 降水確率の平均を計算
        avg_rain = calculate_average_percentage(chance_of_rain)

        results = f"{date}の{title}は{weather}です。\n最高気温は{max_temp}度、最低気温は{min_temp}度\n降水確率の平均は{avg_rain:.1f}%です。\n時間別降水確率: {chance_of_rain}"
        
        return results
    
    except requests.exceptions.RequestException as e:
        return f"天気情報の取得に失敗しました: {e}"
        
    except KeyError as e:
        return f"予期しないデータ形式です: {e}"

if __name__ == "__main__":
    city_number = "140010"
    result = get_weather(1, city_number)
    print(result)