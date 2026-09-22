import os
import numpy as np
import httpx
from sqlalchemy.orm import Session
from ..config import settings
from ..models.problem import Problem
from ..models.submission import Submission

# Try importing the new Google GenAI SDK if available
try:
    from google import genai
    from google.genai import types
    client_available = True
except ImportError:
    client_available = False

class AIService:
    def __init__(self):
        self.api_key = None
        self.client = None
        self.default_model = None
        self.embed_model = None
        self._ensure_client()

    def _ensure_client(self):
        from dotenv import load_dotenv, find_dotenv
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env_path = os.path.join(project_root, ".env")
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path, override=True)
        else:
            load_dotenv(find_dotenv(usecwd=True), override=True)
            
        raw_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", "")
        key = str(raw_key).strip().strip('"').strip("'").strip()
        if key and (not self.api_key or self.api_key != key):
            self.api_key = key
            self._discover_models()

    def _discover_models(self):
        if not self.api_key:
            return
        masked_key = f"{self.api_key[:6]}...{self.api_key[-4:]}" if len(self.api_key) > 10 else "(short/empty)"
        print(f"[*] Validating Gemini API Key: {masked_key}")
        try:
            url = "https://generativelanguage.googleapis.com/v1beta/models"
            headers = {"x-goog-api-key": self.api_key}
            resp = httpx.get(url, headers=headers, params={"key": self.api_key}, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                self.valid_gen_models = []
                self.valid_embed_models = []
                for m in models:
                    name = m.get("name", "").replace("models/", "")
                    methods = m.get("supportedGenerationMethods", [])
                    
                    # Filter out TTS, audio-only, image generation, or discontinued preview models
                    if any(bad in name.lower() for bad in ["tts", "audio", "imagen", "veo", "gemini-2.5"]):
                        continue
                        
                    if "generateContent" in methods:
                        self.valid_gen_models.append(name)
                    if "embedContent" in methods:
                        self.valid_embed_models.append(name)
                
                print(f"[*] Available Text Models: {self.valid_gen_models}")
                
                preferred = [
                    'gemini-flash-latest',
                    'gemini-flash-lite-latest',
                    'gemini-2.0-flash',
                    'gemini-2.0-flash-lite',
                    'gemini-1.5-flash',
                    'gemini-1.5-flash-latest',
                    'gemini-3.5-flash',
                    'gemini-3.7-flash',
                    'gemini-3.5-flash-lite',
                    'gemini-pro-latest',
                    'gemini-1.5-pro'
                ]
                for p in preferred:
                    if p in self.valid_gen_models:
                        self.default_model = p
                        break
                if not self.default_model and self.valid_gen_models:
                    # Filter for gemini models before gemma
                    gemini_mods = [m for m in self.valid_gen_models if m.startswith("gemini-") and "image" not in m]
                    self.default_model = gemini_mods[0] if gemini_mods else self.valid_gen_models[0]
                if self.valid_embed_models:
                    self.embed_model = 'gemini-embedding-001' if 'gemini-embedding-001' in self.valid_embed_models else ('text-embedding-004' if 'text-embedding-004' in self.valid_embed_models else self.valid_embed_models[0])
                print(f"[*] Connected to Google Gemini! Selected Text Model: '{self.default_model}' (Embeddings: '{self.embed_model}')")
            else:
                err_msg = resp.text
                print(f"[!] Google Gemini Key validation notice ({resp.status_code}): {err_msg}")
        except Exception as e:
            print(f"[!] Note on Gemini model discovery: {e}")

    def is_active(self) -> bool:
        self._ensure_client()
        return bool(self.api_key and self.api_key.strip())

    def generate_response(self, prompt: str, system_instruction: str = None) -> str:
        """
        Generates content from Gemini or falls back to mock responses.
        Filters out raw thought/reasoning tokens for clean presentation.
        """
        if self.is_active():
            candidates = []
            if self.default_model:
                candidates.append(self.default_model)
            if hasattr(self, "valid_gen_models") and self.valid_gen_models:
                # Prioritize gemini over gemma
                gemini_mods = [m for m in self.valid_gen_models if m.startswith("gemini-") and "image" not in m]
                candidates.extend(gemini_mods)
                candidates.extend(self.valid_gen_models)
            candidates.extend([
                'gemini-flash-latest',
                'gemini-2.0-flash',
                'gemini-1.5-flash',
                'gemini-flash-lite-latest'
            ])
            
            seen = set()
            unique_candidates = [
                c for c in candidates 
                if not (c in seen or seen.add(c)) and not any(bad in c.lower() for bad in ["tts", "audio", "imagen", "veo", "gemini-2.5", "image"])
            ]
            
            last_err = None
            headers = {
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            for model_name in unique_candidates:
                for api_ver in ['v1beta', 'v1']:
                    try:
                        url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{model_name}:generateContent"
                        payload = {
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {
                                "temperature": 0.4
                            }
                        }
                        if system_instruction:
                            payload["systemInstruction"] = {
                                "parts": [{"text": system_instruction}]
                            }
                        
                        resp = httpx.post(url, headers=headers, params={"key": self.api_key}, json=payload, timeout=35.0)
                        
                        # If systemInstruction was rejected on older model endpoint, retry with merged prompt
                        if resp.status_code == 400 and system_instruction:
                            payload_fallback = {
                                "contents": [{"parts": [{"text": f"SYSTEM INSTRUCTION:\n{system_instruction}\n\nUSER PROMPT:\n{prompt}"}]}],
                                "generationConfig": {"temperature": 0.4}
                            }
                            resp = httpx.post(url, headers=headers, params={"key": self.api_key}, json=payload_fallback, timeout=35.0)

                        if resp.status_code == 200:
                            res_data = resp.json()
                            candidates_list = res_data.get("candidates", [])
                            if candidates_list:
                                content = candidates_list[0].get("content", {})
                                parts = content.get("parts", [])
                                
                                # Filter out thinking parts
                                clean_parts = []
                                for p in parts:
                                    if p.get("thought", False):
                                        continue
                                    txt = p.get("text", "")
                                    if txt:
                                        clean_parts.append(txt)
                                
                                if clean_parts:
                                    self.default_model = model_name
                                    final_text = "".join(clean_parts).strip()
                                    # Strip any inline thinking tags if present
                                    if "</thought>" in final_text:
                                        final_text = final_text.split("</thought>", 1)[1].strip()
                                    return final_text
                        else:
                            last_err = f"HTTP {resp.status_code} ({model_name}, {api_ver}): {resp.text}"
                    except Exception as e:
                        last_err = str(e)
                        continue

            print(f"[!] Gemini generation error across models: {last_err}")
            return f"[Gemini Error: {str(last_err)}]. Switched to Mock Mode."
        
        # Fallback to Mock Response Generator
        return self._generate_mock_response(prompt, system_instruction)

    def get_embedding(self, text: str) -> list:
        """
        Gets embedding vector for text using Gemini.
        Returns list of floats or mock vector of length 768.
        """
        if self.is_active():
            embed_models = []
            if self.embed_model:
                embed_models.append(self.embed_model)
            embed_models.extend(['text-embedding-004', 'embedding-001'])
            
            seen = set()
            unique_embed = [c for c in embed_models if not (c in seen or seen.add(c))]
            
            for model_name in unique_embed:
                for api_ver in ['v1beta', 'v1']:
                    try:
                        url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{model_name}:embedContent?key={self.api_key}"
                        payload = {
                            "content": {"parts": [{"text": text}]}
                        }
                        resp = httpx.post(url, json=payload, timeout=12.0)
                        if resp.status_code == 200:
                            res_data = resp.json()
                            embedding = res_data.get("embedding", {})
                            values = embedding.get("values", [])
                            if values:
                                self.embed_model = model_name
                                return values
                    except Exception:
                        continue
        
        # Mock embedding: deterministic vector based on text length and character sums
        np.random.seed(abs(hash(text)) % (2**32))
        return np.random.rand(768).tolist()

    # --- MAIN AI FEATURES ---

    def analyze_complexity(self, code: str, problem_title: str) -> str:
        system = "You are an expert algorithm educator. Analyze the time and space complexity of the provided user code."
        prompt = f"""Problem: {problem_title}
User Code:
```python
{code}
```

Identify the Big-O Time Complexity and Space Complexity. Suggest any optimizations if possible. Keep it educational and concise.
"""
        return self.generate_response(prompt, system)

    def provide_code_review(self, code: str, problem_title: str, submission_status: str) -> str:
        system = "You are a senior software engineer conducting a peer code review. Focus on best practices, readability, naming conventions, and cleanliness."
        prompt = f"""Problem: {problem_title}
Submission Verdict: {submission_status}
User Code:
```python
{code}
```

Provide a constructive code review. Detail:
1. What went well (naming, logic).
2. Readability improvements.
3. Best practices (e.g. edge cases, pythonic structures).
"""
        return self.generate_response(prompt, system)

    def generate_debug_hints(self, code: str, problem_title: str, error_message: str) -> str:
        system = "You are a coding debugging mentor. Do NOT provide the complete corrected solution code. Instead, explain the error conceptually and give progressive, guiding hints to help the student solve it."
        prompt = f"""Problem: {problem_title}
Error Message / Failure: {error_message}
User Code:
```python
{code}
```

Explain what is causing this issue and provide 2-3 progressive hints. Again, do NOT write the corrected code.
"""
        return self.generate_response(prompt, system)

    def answer_question(self, query: str, problem: Problem, code: str = None, history: list = None) -> str:
        """
        RAG-grounded QA. Injects problem description, constraints, editorials, and the student's current code in the editor.
        """
        system = "You are a computer science teaching assistant. Answer the student's question, grounding your response strictly in the provided Problem Context and their currently written code. Do not output raw drafting notes or thoughts."
        
        code_section = f"\nSTUDENT'S CURRENT CODE IN EDITOR:\n```python\n{code}\n```\n" if code and code.strip() else ""
        
        context = f"""PROBLEM CONTEXT:
Title: {problem.title}
Difficulty: {problem.difficulty.value if hasattr(problem.difficulty, 'value') else problem.difficulty}
Description:
{problem.description}
Tags: {problem.tags}
{code_section}"""
        prompt = f"""{context}

Student Question: {query}
"""
        return self.generate_response(prompt, system)

    def recommend_problems(self, current_problem: Problem, all_problems: list) -> list:
        """
        Uses RAG / semantic similarity.
        Compares embedding of current problem's description/tags with other problems.
        Returns top-2 recommended problems.
        """
        if len(all_problems) <= 1:
            return []
            
        current_vector = self.get_embedding(f"{current_problem.title} {' '.join(current_problem.tags or [])}")
        current_np = np.array(current_vector)
        
        scored_problems = []
        for p in all_problems:
            if p.id == current_problem.id:
                continue
            
            p_vector = self.get_embedding(f"{p.title} {' '.join(p.tags or [])}")
            p_np = np.array(p_vector)
            
            # Cosine similarity
            dot_product = np.dot(current_np, p_np)
            norm_a = np.linalg.norm(current_np)
            norm_b = np.linalg.norm(p_np)
            similarity = dot_product / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else 0.0
            
            scored_problems.append((similarity, p))
            
        # Sort by similarity descending
        scored_problems.sort(key=lambda x: x[0], reverse=True)
        # Return top 2 problems
        return [p for score, p in scored_problems[:2]]

    # --- MOCK RESPONSE ENGINE ---

    def _generate_mock_response(self, prompt: str, system: str) -> str:
        prompt_lower = prompt.lower()
        
        # Check if Two Sum
        is_two_sum = "two sum" in prompt_lower
        is_reverse_string = "reverse string" in prompt_lower or "reverse-string" in prompt_lower
        is_binary_search = "binary search" in prompt_lower or "binary-search" in prompt_lower
        is_valid_parentheses = "valid parentheses" in prompt_lower or "valid-parentheses" in prompt_lower
        is_fibonacci = "fibonacci" in prompt_lower
        
        # Review Mode
        if "code review" in prompt_lower or "review" in system.lower():
            if is_two_sum:
                return """### 🤖 AI Code Review (Mock Mode)

**Overview**: Your solution for **Two Sum** looks solid. Let's analyze its readability and pythonic conventions.

**1. Strengths**:
- Logic for index tracking is present.
- Good variable naming (e.g. using `nums` and `target` matching the problem description).

**2. Readability Improvements**:
- If you used a nested loop ($O(N^2)$), consider extracting it into a single-pass hash map to improve performance.
- Use Python's `enumerate()` for cleaner index handling rather than a manual counter:
  ```python
  for index, value in enumerate(nums):
      # code...
  ```

**3. Best Practices**:
- Consider adding type hinting: `def two_sum(nums: list[int], target: int) -> list[int]`.
- Always check if inputs can be empty or have fewer than two elements as defensive validation.
"""
            elif is_reverse_string:
                return """### 🤖 AI Code Review (Mock Mode)

**Overview**: Nice job on reversing the string.
- If you used `s[::-1]`, that is the most efficient and pythonic way in CPython.
- If you used a two-pointer approach, it displays strong algorithmic fundamentals!
"""
            else:
                return "### 🤖 AI Code Review (Mock Mode)\nYour solution looks clean and correct. Pay attention to edge cases like empty inputs, single element arrays, and integer overflow constraints."

        # Complexity Mode
        elif "complexity" in prompt_lower or "complexity" in system.lower():
            if "for " in prompt and "for " in prompt.split("for ", 1)[1]: # nested loop heuristic
                return r"""### 📊 Complexity Analysis (Mock Mode)

- **Time Complexity**: $\mathcal{O}(N^2)$ where $N$ is the length of the input. This is due to the nested loop scanning all pairs.
- **Space Complexity**: $\mathcal{O}(1)$ since you are using only a constant amount of extra memory space.
- **Optimization**: You can reduce the time complexity to $\mathcal{O}(N)$ using a Hash Map to store numbers and their indices!
"""
            else:
                return r"""### 📊 Complexity Analysis (Mock Mode)

- **Time Complexity**: $\mathcal{O}(N)$ where $N$ is the number of elements. We traverse the input array exactly once.
- **Space Complexity**: $\mathcal{O}(N)$ in the worst case to store the visited items in our Hash Map.
"""

        # Debug Mode
        elif "debug" in prompt_lower or "debug" in system.lower():
            return """### 🔧 Debugger Assistant (Mock Mode)

It looks like your code encountered a failure or didn't produce the expected output.
- **Hint 1**: Trace the execution for the smallest input (e.g., list of size 2, or an empty string).
- **Hint 2**: Check if you are double-using the same element. Remember, you cannot use the same index twice.
- **Hint 3**: Print out the state of variables right before the return statement to verify if they match expectations.
"""

        # General Question Answering
        else:
            return r"""### 💡 AI Mentor Response (Mock Mode)

I am here to help you study coding algorithms!
- To optimize your code, try to use a Hash Map to trade space for time (reducing $\mathcal{O}(N^2)$ to $\mathcal{O}(N)$).
- Make sure to handle potential boundary conditions (like target values that are negative, or elements not found).
- Let me know if you would like a code review, complexity analysis, or debugging hints for your submission!
"""

ai_service = AIService()
