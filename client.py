import requests


def summon_oracle():
  try:
    url = "http://127.0.0.1:8000/oracle"  # Replace with your actual Replit URL
    response = requests.get(url)
    if response.status_code == 200:
      return response.text.strip()
    else:
      return f"Oracle error: {response.status_code}"
  except Exception as e:
    return f"Oracle connection failed: {e}"


if __name__ == "__main__":
  print("42 is invoking the Oracle...")
  prophecy = summon_oracle()
  print("\n🔮 Prophecy from the Oracle:\n")
  print(prophecy)
