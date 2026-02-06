import json, os, re, time
from groq import Groq
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class AIAuditor:
    def __init__(self):
        self.use_openai = os.getenv("OPENAI_AUDIT_ENABLED", "false").lower() == "true"
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None
        if os.getenv("GEMINI_API_KEY"): genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if self.use_openai and os.getenv("OPENAI_API_KEY") else None

    def audit(self, signal, sentiment):
        try:
            if self.use_openai and self.openai_client:
                return self._audit_premium(signal, sentiment)
            return self._audit_standard(signal, sentiment)
        except Exception as e:
            return {"status": "REJECTED", "risk_level": "HIGH", "reason": f"FAIL_CLOSED: {str(e)}"}

    def _audit_standard(self, signal, sentiment):
        if self.groq_client:
            try: return self._call_groq(signal, sentiment)
            except: pass
        try: return self._call_gemini(signal, sentiment)
        except: return {"status": "REJECTED", "risk_level": "HIGH", "reason": "ALL AI FAILED"}

    def _audit_premium(self, signal, sentiment):
        try: return self._call_openai(signal, sentiment)
        except: return self._audit_standard(signal, sentiment)

    def _validate(self, text):
        try:
            text = text.replace("```json", "").replace("```", "").strip()
            match = re.search(r"\{[\s\S]*?\}", text)
            if not match: return {"status": "REJECTED", "risk_level": "HIGH", "reason": "NO JSON"}
            data = json.loads(match.group(0))
            
            required = ["status", "risk_level", "reason"]
            if not all(k in data for k in required): return {"status": "REJECTED", "risk_level": "HIGH", "reason": "SCHEMA ERROR"}
            
            if data["risk_level"] != "LOW": data["status"] = "REJECTED"
            return data
        except: return {"status": "REJECTED", "risk_level": "HIGH", "reason": "PARSE ERROR"}

    def _call_groq(self, signal, sentiment):
        prompt = f'AUDIT TRADE.\nSignal: {signal}\nNews: {sentiment}\nReturn strict JSON: {{"status":"APPROVED|REJECTED", "risk_level":"LOW|MEDIUM|HIGH", "reason":"str"}}'
        resp = self.groq_client.chat.completions.create(
            model="llama3-70b-8192", messages=[{"role": "user", "content": prompt}], temperature=0, timeout=5.0
        )
        return self._validate(resp.choices[0].message.content)

    def _call_gemini(self, signal, sentiment):
        prompt = f'AUDIT TRADE.\nSignal: {signal}\nNews: {sentiment}\nReturn strict JSON: {{"status":"APPROVED|REJECTED", "risk_level":"LOW|MEDIUM|HIGH", "reason":"str"}}'
        resp = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)
        return self._validate(resp.text)

    def _call_openai(self, signal, sentiment):
        prompt = f'AUDIT TRADE.\nSignal: {signal}\nNews: {sentiment}\nReturn strict JSON: {{"status":"APPROVED|REJECTED", "risk_level":"LOW|MEDIUM|HIGH", "reason":"str"}}'
        resp = self.openai_client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"}, temperature=0, timeout=5.0
        )
        return json.loads(resp.choices[0].message.content)
