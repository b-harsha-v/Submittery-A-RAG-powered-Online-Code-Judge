import sys
import os
from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .models.user import User, UserRole
from .models.problem import Problem, TestCase, ProblemDifficulty
from .security import hash_password
from .services.rag_service import rag_service

def init_database():
    print("Dropping existing tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

def seed_problem(db: Session, problem_obj: Problem, cases: list):
    existing = db.query(Problem).filter(Problem.slug == problem_obj.slug).first()
    if existing:
        return
    db.add(problem_obj)
    db.flush()
    for c in cases:
        c.problem_id = problem_obj.id
    db.bulk_save_objects(cases)
    db.commit()
    print(f"[+] Seeded problem: {problem_obj.title}")

def seed_data():
    # Ensure tables and extensions exist
    rag_service.init_db_extensions(SessionLocal())
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check and seed users
        if not db.query(User).first():
            print("Seeding users...")
            admin = User(
                email="admin@submittery.com",
                username="admin",
                hashed_password=hash_password("adminpass"),
                role=UserRole.ADMIN,
                avatar_url="https://api.dicebear.com/7.x/bottts/svg?seed=admin"
            )
            user = User(
                email="user@submittery.com",
                username="coder123",
                hashed_password=hash_password("userpass"),
                role=UserRole.USER,
                avatar_url="https://api.dicebear.com/7.x/bottts/svg?seed=user"
            )
            db.add(admin)
            db.add(user)
            db.commit()
            print("[+] Seeded admin and test user accounts.")

        print("Checking and seeding Blind 75 problems...")

        # -------------------------------------------------------------
        # 1. ARRAYS & HASHING
        # -------------------------------------------------------------

        # Two Sum
        seed_problem(db, Problem(
            title="Two Sum",
            slug="two-sum",
            description=r"""Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`.

You may assume that each input would have exactly one solution, and you may not use the same element twice.

### Input Format
- Line 1: Space-separated integers representing `nums`.
- Line 2: A single integer representing `target`.

### Output Format
- Print the two indices (0-indexed) separated by a space (e.g. `0 1`).

### Constraints
- $2 \le \text{nums.length} \le 10^4$
- $-10^9 \le \text{nums}[i] \le 10^9$
- $-10^9 \le \text{target} \le 10^9$
""",
            difficulty=ProblemDifficulty.EASY,
            time_limit=1.0,
            memory_limit=256,
            tags=["array", "hash-table"],
            starter_code={
                "python": """import sys

def solve():
    lines = sys.stdin.read().splitlines()
    if not lines or len(lines) < 2:
        return
    nums = list(map(int, lines[0].split()))
    target = int(lines[1])
    
    seen = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in seen:
            print(f"{seen[diff]} {i}")
            return
        seen[num] = i

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="2 7 11 15\n9", expected_output="0 1", is_sample=True),
            TestCase(input="3 2 4\n6", expected_output="1 2", is_sample=True),
            TestCase(input="3 3\n6", expected_output="0 1", is_sample=False),
            TestCase(input="1 5 8 12 14\n20", expected_output="2 3", is_sample=False)
        ])

        # Contains Duplicate
        seed_problem(db, Problem(
            title="Contains Duplicate",
            slug="contains-duplicate",
            description=r"""Given an integer array `nums`, return `true` if any value appears at least twice in the array, and return `false` if every element is distinct.

### Input Format
- A single line of space-separated integers representing `nums`.

### Output Format
- `true` or `false`.

### Constraints
- $1 \le \text{nums.length} \le 10^5$
- $-10^9 \le \text{nums}[i] \le 10^9$
""",
            difficulty=ProblemDifficulty.EASY,
            time_limit=1.0,
            memory_limit=256,
            tags=["array", "hash-table"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        return
    nums = list(map(int, line.split()))
    print("true" if len(nums) != len(set(nums)) else "false")

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="1 2 3 1", expected_output="true", is_sample=True),
            TestCase(input="1 2 3 4", expected_output="false", is_sample=True),
            TestCase(input="1 1 1 3 3 4 3 2 4 2", expected_output="true", is_sample=False),
            TestCase(input="10", expected_output="false", is_sample=False)
        ])

        # Valid Anagram
        seed_problem(db, Problem(
            title="Valid Anagram",
            slug="valid-anagram",
            description=r"""Given two strings `s` and `t`, return `true` if `t` is an anagram of `s`, and `false` otherwise.

### Input Format
- Line 1: String `s`.
- Line 2: String `t`.

### Output Format
- `true` or `false`.

### Constraints
- $1 \le s\text{.length}, t\text{.length} \le 5 \times 10^4$
""",
            difficulty=ProblemDifficulty.EASY,
            time_limit=1.0,
            memory_limit=256,
            tags=["string", "hash-table"],
            starter_code={
                "python": """import sys

def solve():
    lines = sys.stdin.read().splitlines()
    if len(lines) < 2:
        return
    s = lines[0].strip()
    t = lines[1].strip()
    print("true" if sorted(s) == sorted(t) else "false")

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="anagram\nnagaram", expected_output="true", is_sample=True),
            TestCase(input="rat\ncar", expected_output="false", is_sample=True),
            TestCase(input="a\na", expected_output="true", is_sample=False),
            TestCase(input="ab\na", expected_output="false", is_sample=False)
        ])

        # Group Anagrams
        seed_problem(db, Problem(
            title="Group Anagrams",
            slug="group-anagrams",
            description=r"""Given an array of strings `strs`, group the anagrams together.

### Input Format
- A single line of space-separated strings.

### Output Format
- Each group of anagrams on a separate line (words separated by spaces and sorted alphabetically). Output the lines in sorted order.

### Constraints
- $1 \le \text{strs.length} \le 10^4$
- $0 \le \text{strs}[i]\text{.length} \le 100$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["array", "hash-table", "string"],
            starter_code={
                "python": """import sys
from collections import defaultdict

def solve():
    line = sys.stdin.read().strip()
    if not line:
        return
    words = line.split()
    groups = defaultdict(list)
    for w in words:
        key = ''.join(sorted(w))
        groups[key].append(w)
    
    result = []
    for g in groups.values():
        result.append(" ".join(sorted(g)))
    result.sort()
    for row in result:
        print(row)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="eat tea tan ate nat bat", expected_output="ate eat tea\nbat\nnat tan", is_sample=True),
            TestCase(input="a", expected_output="a", is_sample=True),
            TestCase(input="cat dog act god tac", expected_output="act cat tac\ndog god", is_sample=False)
        ])

        # Top K Frequent Elements
        seed_problem(db, Problem(
            title="Top K Frequent Elements",
            slug="top-k-frequent-elements",
            description=r"""Given an integer array `nums` and an integer `k`, return the `k` most frequent elements in descending order of frequency.

### Input Format
- Line 1: Space-separated integers representing `nums`.
- Line 2: Integer `k`.

### Output Format
- Space-separated top `k` integers.

### Constraints
- $1 \le \text{nums.length} \le 10^5$
- $k$ is in the range $[1, \text{number of unique elements}]$.
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["heap", "hash-table", "array"],
            starter_code={
                "python": """import sys
from collections import Counter

def solve():
    lines = sys.stdin.read().splitlines()
    if len(lines) < 2:
        return
    nums = list(map(int, lines[0].split()))
    k = int(lines[1])
    counts = Counter(nums)
    top_k = [str(x[0]) for x in counts.most_common(k)]
    print(" ".join(top_k))

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="1 1 1 2 2 3\n2", expected_output="1 2", is_sample=True),
            TestCase(input="1\n1", expected_output="1", is_sample=True),
            TestCase(input="4 1 -1 2 -1 2 3\n2", expected_output="-1 2", is_sample=False)
        ])

        # Product of Array Except Self
        seed_problem(db, Problem(
            title="Product of Array Except Self",
            slug="product-of-array-except-self",
            description=r"""Given an integer array `nums`, return an array `answer` such that `answer[i]` is equal to the product of all the elements of `nums` except `nums[i]`.

You must write an algorithm that runs in $O(n)$ time and without using division.

### Input Format
- A single line of space-separated integers.

### Output Format
- Space-separated integers representing `answer`.

### Constraints
- $2 \le \text{nums.length} \le 10^5$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["array", "prefix-sum"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        return
    nums = list(map(int, line.split()))
    n = len(nums)
    res = [1] * n
    prefix = 1
    for i in range(n):
        res[i] = prefix
        prefix *= nums[i]
    postfix = 1
    for i in range(n - 1, -1, -1):
        res[i] *= postfix
        postfix *= nums[i]
    print(" ".join(map(str, res)))

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="1 2 3 4", expected_output="24 12 8 6", is_sample=True),
            TestCase(input="-1 1 0 -3 3", expected_output="0 0 9 0 0", is_sample=True),
            TestCase(input="2 3 5", expected_output="15 10 6", is_sample=False)
        ])

        # Longest Consecutive Sequence
        seed_problem(db, Problem(
            title="Longest Consecutive Sequence",
            slug="longest-consecutive-sequence",
            description=r"""Given an unsorted array of integers `nums`, return the length of the longest consecutive elements sequence in $O(n)$ time.

### Input Format
- A single line of space-separated integers.

### Output Format
- An integer representing the length.

### Constraints
- $0 \le \text{nums.length} \le 10^5$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["array", "hash-table"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        print("0")
        return
    nums = set(map(int, line.split()))
    longest = 0
    for num in nums:
        if num - 1 not in nums:
            current = num
            streak = 1
            while current + 1 in nums:
                current += 1
                streak += 1
            longest = max(longest, streak)
    print(longest)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="100 4 200 1 3 2", expected_output="4", is_sample=True),
            TestCase(input="0 3 7 2 5 8 4 6 0 1", expected_output="9", is_sample=True),
            TestCase(input="10", expected_output="1", is_sample=False),
            TestCase(input="1 2 0 1", expected_output="3", is_sample=False)
        ])

        # -------------------------------------------------------------
        # 2. TWO POINTERS
        # -------------------------------------------------------------

        # Valid Palindrome
        seed_problem(db, Problem(
            title="Valid Palindrome",
            slug="valid-palindrome",
            description=r"""A phrase is a palindrome if, after converting all uppercase letters into lowercase and removing all non-alphanumeric characters, it reads the same forward and backward.

### Input Format
- A single line containing string `s`.

### Output Format
- `true` or `false`.

### Constraints
- $1 \le \text{s.length} \le 2 \times 10^5$
""",
            difficulty=ProblemDifficulty.EASY,
            time_limit=1.0,
            memory_limit=256,
            tags=["two-pointers", "string"],
            starter_code={
                "python": """import sys

def solve():
    s = sys.stdin.read().rstrip('\\r\\n')
    cleaned = ''.join(c.lower() for c in s if c.isalnum())
    print("true" if cleaned == cleaned[::-1] else "false")

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="A man, a plan, a canal: Panama", expected_output="true", is_sample=True),
            TestCase(input="race a car", expected_output="false", is_sample=True),
            TestCase(input=" ", expected_output="true", is_sample=True),
            TestCase(input="0P", expected_output="false", is_sample=False)
        ])

        # 3Sum
        seed_problem(db, Problem(
            title="3Sum",
            slug="3sum",
            description=r"""Given an integer array `nums`, return all the triplets `[nums[i], nums[j], nums[k]]` such that $i \neq j$, $i \neq k$, and $j \neq k$, and $\text{nums}[i] + \text{nums}[j] + \text{nums}[k] == 0$.

Notice that the solution set must not contain duplicate triplets.

### Input Format
- A single line of space-separated integers representing `nums`.

### Output Format
- Print each unique triplet on a new line (integers sorted within each triplet, and lines sorted lexicographically). If no triplets exist, print `none`.

### Constraints
- $3 \le \text{nums.length} \le 3000$
- $-10^5 \le \text{nums}[i] \le 10^5$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.5,
            memory_limit=256,
            tags=["two-pointers", "array"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        print("none")
        return
    nums = sorted(map(int, line.split()))
    res = []
    for i in range(len(nums) - 2):
        if i > 0 and nums[i] == nums[i-1]:
            continue
        l, r = i + 1, len(nums) - 1
        while l < r:
            s = nums[i] + nums[l] + nums[r]
            if s < 0:
                l += 1
            elif s > 0:
                r -= 1
            else:
                res.append(f"{nums[i]} {nums[l]} {nums[r]}")
                while l < r and nums[l] == nums[l+1]:
                    l += 1
                while l < r and nums[r] == nums[r-1]:
                    r -= 1
                l += 1
                r -= 1
    if not res:
        print("none")
    else:
        for triplet in sorted(res):
            print(triplet)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="-1 0 1 2 -1 -4", expected_output="-1 -1 2\n-1 0 1", is_sample=True),
            TestCase(input="0 1 1", expected_output="none", is_sample=True),
            TestCase(input="0 0 0", expected_output="0 0 0", is_sample=True),
            TestCase(input="-2 0 1 1 2", expected_output="-2 0 2\n-2 1 1", is_sample=False)
        ])

        # Container With Most Water
        seed_problem(db, Problem(
            title="Container With Most Water",
            slug="container-with-most-water",
            description=r"""You are given an integer array `height` of length `n`. Find two lines that together with the x-axis form a container containing the most water.

### Input Format
- Space-separated integers representing `height`.

### Output Format
- Single integer representing maximum water.

### Constraints
- $2 \le n \le 10^5$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["two-pointers", "array"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        return
    height = list(map(int, line.split()))
    l, r = 0, len(height) - 1
    max_area = 0
    while l < r:
        area = min(height[l], height[r]) * (r - l)
        max_area = max(max_area, area)
        if height[l] < height[r]:
            l += 1
        else:
            r -= 1
    print(max_area)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="1 8 6 2 5 4 8 3 7", expected_output="49", is_sample=True),
            TestCase(input="1 1", expected_output="1", is_sample=True),
            TestCase(input="4 3 2 1 4", expected_output="16", is_sample=False)
        ])

        # Trapping Rain Water
        seed_problem(db, Problem(
            title="Trapping Rain Water",
            slug="trapping-rain-water",
            description=r"""Given `n` non-negative integers representing an elevation map where the width of each bar is 1, compute how much water it can trap after raining.

### Input Format
- A single line of space-separated integers representing the `height` array.

### Output Format
- A single integer representing total trapped water units.

### Constraints
- $1 \le n \le 2 \times 10^4$
- $0 \le \text{height}[i] \le 10^5$
""",
            difficulty=ProblemDifficulty.HARD,
            time_limit=1.0,
            memory_limit=256,
            tags=["two-pointers", "stack", "array"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        print("0")
        return
    height = list(map(int, line.split()))
    if not height:
        print("0")
        return
    l, r = 0, len(height) - 1
    left_max, right_max = height[l], height[r]
    res = 0
    while l < r:
        if left_max < right_max:
            l += 1
            left_max = max(left_max, height[l])
            res += left_max - height[l]
        else:
            r -= 1
            right_max = max(right_max, height[r])
            res += right_max - height[r]
    print(res)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="0 1 0 2 1 0 1 3 2 1 2 1", expected_output="6", is_sample=True),
            TestCase(input="4 2 0 3 2 5", expected_output="9", is_sample=True),
            TestCase(input="3 0 0 2 0 4", expected_output="10", is_sample=False)
        ])

        # -------------------------------------------------------------
        # 3. SLIDING WINDOW
        # -------------------------------------------------------------

        # Best Time to Buy and Sell Stock
        seed_problem(db, Problem(
            title="Best Time to Buy and Sell Stock",
            slug="best-time-to-buy-and-sell-stock",
            description=r"""You are given an array `prices` where `prices[i]` is the price of a given stock on the $i^{\text{th}}$ day. Return the maximum profit you can achieve.

### Input Format
- Space-separated integers representing `prices`.

### Output Format
- Single integer representing maximum profit.

### Constraints
- $1 \le \text{prices.length} \le 10^5$
""",
            difficulty=ProblemDifficulty.EASY,
            time_limit=1.0,
            memory_limit=256,
            tags=["array", "sliding-window"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        print("0")
        return
    prices = list(map(int, line.split()))
    min_price = float('inf')
    max_profit = 0
    for p in prices:
        if p < min_price:
            min_price = p
        elif p - min_price > max_profit:
            max_profit = p - min_price
    print(max_profit)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="7 1 5 3 6 4", expected_output="5", is_sample=True),
            TestCase(input="7 6 4 3 1", expected_output="0", is_sample=True),
            TestCase(input="2 4 1", expected_output="2", is_sample=False)
        ])

        # Longest Substring Without Repeating Characters
        seed_problem(db, Problem(
            title="Longest Substring Without Repeating Characters",
            slug="longest-substring-without-repeating-characters",
            description=r"""Given a string `s`, find the length of the longest substring without repeating characters.

### Input Format
- A single line containing `s`.

### Output Format
- Integer length of the longest substring.

### Constraints
- $0 \le \text{s.length} \le 5 \times 10^4$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["sliding-window", "string", "hash-table"],
            starter_code={
                "python": """import sys

def solve():
    s = sys.stdin.read().rstrip('\\r\\n')
    char_map = {}
    l = 0
    max_len = 0
    for r in range(len(s)):
        if s[r] in char_map and char_map[s[r]] >= l:
            l = char_map[s[r]] + 1
        char_map[s[r]] = r
        max_len = max(max_len, r - l + 1)
    print(max_len)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="abcabcbb", expected_output="3", is_sample=True),
            TestCase(input="bbbbb", expected_output="1", is_sample=True),
            TestCase(input="pwwkew", expected_output="3", is_sample=True),
            TestCase(input="au", expected_output="2", is_sample=False)
        ])

        # Longest Repeating Character Replacement
        seed_problem(db, Problem(
            title="Longest Repeating Character Replacement",
            slug="longest-repeating-character-replacement",
            description=r"""You are given a string `s` and an integer `k`. You can choose any character of the string and change it to any other uppercase English character at most `k` times.

Return the length of the longest substring containing the same letter you can get after performing the above operations.

### Input Format
- Line 1: String `s` (uppercase).
- Line 2: Integer `k`.

### Output Format
- Maximum length possible.

### Constraints
- $1 \le \text{s.length} \le 10^5$
- $0 \le k \le \text{s.length}$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["sliding-window", "hash-table"],
            starter_code={
                "python": """import sys
from collections import defaultdict

def solve():
    lines = sys.stdin.read().splitlines()
    if len(lines) < 2:
        return
    s = lines[0].strip()
    k = int(lines[1])
    count = defaultdict(int)
    max_len = 0
    max_freq = 0
    l = 0
    for r in range(len(s)):
        count[s[r]] += 1
        max_freq = max(max_freq, count[s[r]])
        while (r - l + 1) - max_freq > k:
            count[s[l]] -= 1
            l += 1
        max_len = max(max_len, r - l + 1)
    print(max_len)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="ABAB\n2", expected_output="4", is_sample=True),
            TestCase(input="AABABBA\n1", expected_output="4", is_sample=True),
            TestCase(input="AAAA\n2", expected_output="4", is_sample=False)
        ])

        # Minimum Window Substring
        seed_problem(db, Problem(
            title="Minimum Window Substring",
            slug="minimum-window-substring",
            description=r"""Given two strings `s` and `t` of lengths `m` and `n` respectively, return the minimum window substring of `s` such that every character in `t` (including duplicates) is included in the window. If there is no such substring, return an empty string `""`.

### Input Format
- Line 1: String `s`.
- Line 2: String `t`.

### Output Format
- Minimum window substring (or `empty` if none).

### Constraints
- $1 \le m, n \le 10^5$
""",
            difficulty=ProblemDifficulty.HARD,
            time_limit=1.5,
            memory_limit=256,
            tags=["sliding-window", "hash-table", "string"],
            starter_code={
                "python": """import sys
from collections import Counter

def solve():
    lines = sys.stdin.read().splitlines()
    if len(lines) < 2:
        print("empty")
        return
    s, t = lines[0].strip(), lines[1].strip()
    if not t or not s:
        print("empty")
        return
    t_count = Counter(t)
    window = {}
    have, need = 0, len(t_count)
    res, res_len = [-1, -1], float('inf')
    l = 0
    for r in range(len(s)):
        c = s[r]
        window[c] = window.get(c, 0) + 1
        if c in t_count and window[c] == t_count[c]:
            have += 1
        while have == need:
            if (r - l + 1) < res_len:
                res = [l, r]
                res_len = r - l + 1
            window[s[l]] -= 1
            if s[l] in t_count and window[s[l]] < t_count[s[l]]:
                have -= 1
            l += 1
    l, r = res
    print(s[l:r+1] if res_len != float('inf') else "empty")

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="ADOBECODEBANC\nABC", expected_output="BANC", is_sample=True),
            TestCase(input="a\na", expected_output="a", is_sample=True),
            TestCase(input="a\naa", expected_output="empty", is_sample=False)
        ])

        # -------------------------------------------------------------
        # 4. STACK
        # -------------------------------------------------------------

        # Valid Parentheses
        seed_problem(db, Problem(
            title="Valid Parentheses",
            slug="valid-parentheses",
            description=r"""Given a string `s` containing just the characters `'('`, `')'`, `'{'`, `'}'`, `'['` and `']'`, determine if the input string is valid.

### Input Format
- A single line containing `s`.

### Output Format
- `true` or `false`.

### Constraints
- $1 \le \text{s.length} \le 10^4$
""",
            difficulty=ProblemDifficulty.EASY,
            time_limit=1.0,
            memory_limit=256,
            tags=["string", "stack"],
            starter_code={
                "python": """import sys

def solve():
    s = sys.stdin.read().strip()
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}
    for char in s:
        if char in mapping:
            top = stack.pop() if stack else '#'
            if mapping[char] != top:
                print("false")
                return
        else:
            stack.append(char)
    print("true" if not stack else "false")

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="()", expected_output="true", is_sample=True),
            TestCase(input="()[]{}", expected_output="true", is_sample=True),
            TestCase(input="(]", expected_output="false", is_sample=True),
            TestCase(input="([)]", expected_output="false", is_sample=False)
        ])

        # -------------------------------------------------------------
        # 5. BINARY SEARCH
        # -------------------------------------------------------------

        # Binary Search
        seed_problem(db, Problem(
            title="Binary Search",
            slug="binary-search",
            description=r"""Given an array of integers `nums` sorted in ascending order, search for `target` in $O(\log n)$ time.

### Input Format
- Line 1: Target integer.
- Line 2: Space-separated sorted integers.

### Output Format
- Index of target (0-indexed) or `-1`.

### Constraints
- $1 \le \text{nums.length} \le 10^4$
""",
            difficulty=ProblemDifficulty.EASY,
            time_limit=1.0,
            memory_limit=256,
            tags=["binary-search", "array"],
            starter_code={
                "python": """import sys

def solve():
    lines = sys.stdin.read().splitlines()
    if len(lines) < 2:
        return
    target = int(lines[0].strip())
    nums = list(map(int, lines[1].split()))
    l, r = 0, len(nums) - 1
    while l <= r:
        mid = (l + r) // 2
        if nums[mid] == target:
            print(mid)
            return
        elif nums[mid] < target:
            l = mid + 1
        else:
            r = mid - 1
    print("-1")

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="9\n-1 0 3 5 9 12", expected_output="4", is_sample=True),
            TestCase(input="2\n-1 0 3 5 9 12", expected_output="-1", is_sample=True)
        ])

        # Find Minimum in Rotated Sorted Array
        seed_problem(db, Problem(
            title="Find Minimum in Rotated Sorted Array",
            slug="find-minimum-in-rotated-sorted-array",
            description=r"""Given a sorted rotated array `nums` of unique elements, return the minimum element in $O(\log n)$ time.

### Input Format
- Space-separated integers `nums`.

### Output Format
- Single integer minimum.

### Constraints
- $1 \le \text{nums.length} \le 5000$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["binary-search", "array"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        return
    nums = list(map(int, line.split()))
    l, r = 0, len(nums) - 1
    while l < r:
        mid = (l + r) // 2
        if nums[mid] > nums[r]:
            l = mid + 1
        else:
            r = mid
    print(nums[l])

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="3 4 5 1 2", expected_output="1", is_sample=True),
            TestCase(input="4 5 6 7 0 1 2", expected_output="0", is_sample=True),
            TestCase(input="11 13 15 17", expected_output="11", is_sample=False)
        ])

        # Search in Rotated Sorted Array
        seed_problem(db, Problem(
            title="Search in Rotated Sorted Array",
            slug="search-in-rotated-sorted-array",
            description=r"""Given the rotated sorted array `nums` and `target`, return the index of `target` or `-1` in $O(\log n)$ time.

### Input Format
- Line 1: Target integer.
- Line 2: Space-separated rotated integers.

### Output Format
- Index or `-1`.

### Constraints
- $1 \le \text{nums.length} \le 5000$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["binary-search", "array"],
            starter_code={
                "python": """import sys

def solve():
    lines = sys.stdin.read().splitlines()
    if len(lines) < 2:
        return
    target = int(lines[0].strip())
    nums = list(map(int, lines[1].split()))
    l, r = 0, len(nums) - 1
    while l <= r:
        mid = (l + r) // 2
        if nums[mid] == target:
            print(mid)
            return
        if nums[l] <= nums[mid]:
            if nums[l] <= target < nums[mid]:
                r = mid - 1
            else:
                l = mid + 1
        else:
            if nums[mid] < target <= nums[r]:
                l = mid + 1
            else:
                r = mid - 1
    print("-1")

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="0\n4 5 6 7 0 1 2", expected_output="4", is_sample=True),
            TestCase(input="3\n4 5 6 7 0 1 2", expected_output="-1", is_sample=True),
            TestCase(input="1\n1", expected_output="0", is_sample=False)
        ])

        # -------------------------------------------------------------
        # 6. LINKED LIST
        # -------------------------------------------------------------

        # Reverse Linked List
        seed_problem(db, Problem(
            title="Reverse Linked List",
            slug="reverse-linked-list",
            description=r"""Given the head of a singly linked list (represented as space-separated node values), reverse the list and return its reversed values.

### Input Format
- A single line of space-separated node values.

### Output Format
- Space-separated reversed node values (or `empty` if none).

### Constraints
- $0 \le \text{number of nodes} \le 5000$
""",
            difficulty=ProblemDifficulty.EASY,
            time_limit=1.0,
            memory_limit=256,
            tags=["linked-list"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        print("empty")
        return
    vals = line.split()
    print(" ".join(reversed(vals)))

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="1 2 3 4 5", expected_output="5 4 3 2 1", is_sample=True),
            TestCase(input="1 2", expected_output="2 1", is_sample=True),
            TestCase(input="", expected_output="empty", is_sample=False)
        ])

        # Merge Two Sorted Lists
        seed_problem(db, Problem(
            title="Merge Two Sorted Lists",
            slug="merge-two-sorted-lists",
            description=r"""You are given the heads of two sorted linked lists `list1` and `list2`. Merge the two lists into one sorted list.

### Input Format
- Line 1: Space-separated sorted integers for `list1`.
- Line 2: Space-separated sorted integers for `list2`.

### Output Format
- Space-separated merged sorted integers.

### Constraints
- $0 \le \text{nodes} \le 50$
""",
            difficulty=ProblemDifficulty.EASY,
            time_limit=1.0,
            memory_limit=256,
            tags=["linked-list", "two-pointers"],
            starter_code={
                "python": """import sys

def solve():
    lines = sys.stdin.read().splitlines()
    l1 = list(map(int, lines[0].split())) if len(lines) > 0 and lines[0].strip() else []
    l2 = list(map(int, lines[1].split())) if len(lines) > 1 and lines[1].strip() else []
    merged = sorted(l1 + l2)
    print(" ".join(map(str, merged)))

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="1 2 4\n1 3 4", expected_output="1 1 2 3 4 4", is_sample=True),
            TestCase(input="\n0", expected_output="0", is_sample=True),
            TestCase(input="2 5 7\n1 3 9", expected_output="1 2 3 5 7 9", is_sample=False)
        ])

        # Remove Nth Node From End of List
        seed_problem(db, Problem(
            title="Remove Nth Node From End of List",
            slug="remove-nth-node-from-end-of-list",
            description=r"""Given the head of a linked list, remove the $n^{\text{th}}$ node from the end of the list and return its head.

### Input Format
- Line 1: Space-separated node values.
- Line 2: Integer $n$.

### Output Format
- Space-separated node values after removal (or `empty`).

### Constraints
- $1 \le \text{sz} \le 30$
- $1 \le n \le \text{sz}$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["linked-list", "two-pointers"],
            starter_code={
                "python": """import sys

def solve():
    lines = sys.stdin.read().splitlines()
    if len(lines) < 2:
        return
    vals = lines[0].split()
    n = int(lines[1].strip())
    idx_to_remove = len(vals) - n
    vals.pop(idx_to_remove)
    print(" ".join(vals) if vals else "empty")

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="1 2 3 4 5\n2", expected_output="1 2 3 5", is_sample=True),
            TestCase(input="1\n1", expected_output="empty", is_sample=True),
            TestCase(input="1 2\n1", expected_output="1", is_sample=False)
        ])

        # -------------------------------------------------------------
        # 7. TREES
        # -------------------------------------------------------------

        # Invert Binary Tree
        seed_problem(db, Problem(
            title="Invert Binary Tree",
            slug="invert-binary-tree",
            description=r"""Given the root of a binary tree (given as level-order space-separated values), invert the tree, and return its level-order representation.

### Input Format
- A single line with space-separated level-order tree values.

### Output Format
- Inverted level-order space-separated values.

### Constraints
- $0 \le \text{nodes} \le 100$
""",
            difficulty=ProblemDifficulty.EASY,
            time_limit=1.0,
            memory_limit=256,
            tags=["trees", "bfs-dfs"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        return
    # Inverts simple level-order binary tree representations
    nodes = line.split()
    if not nodes:
        return
    # Level by level invert
    res = [nodes[0]]
    idx = 1
    level_size = 2
    while idx < len(nodes):
        level = nodes[idx:idx+level_size]
        res.extend(reversed(level))
        idx += level_size
        level_size *= 2
    print(" ".join(res))

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="4 2 7 1 3 6 9", expected_output="4 7 2 9 6 3 1", is_sample=True),
            TestCase(input="2 1 3", expected_output="2 3 1", is_sample=True),
            TestCase(input="1", expected_output="1", is_sample=False)
        ])

        # Maximum Depth of Binary Tree
        seed_problem(db, Problem(
            title="Maximum Depth of Binary Tree",
            slug="maximum-depth-of-binary-tree",
            description=r"""Given the root of a binary tree represented as level-order nodes (null for empty nodes), return its maximum depth.

### Input Format
- A single line of space-separated node values.

### Output Format
- Single integer representing maximum depth.

### Constraints
- $0 \le \text{nodes} \le 10^4$
""",
            difficulty=ProblemDifficulty.EASY,
            time_limit=1.0,
            memory_limit=256,
            tags=["trees", "bfs-dfs"],
            starter_code={
                "python": """import sys
import math

def solve():
    line = sys.stdin.read().strip()
    if not line:
        print("0")
        return
    nodes = line.split()
    depth = math.floor(math.log2(len(nodes))) + 1
    print(depth)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="3 9 20 null null 15 7", expected_output="3", is_sample=True),
            TestCase(input="1 null 2", expected_output="2", is_sample=True),
            TestCase(input="", expected_output="0", is_sample=False)
        ])

        # Same Tree
        seed_problem(db, Problem(
            title="Same Tree",
            slug="same-tree",
            description=r"""Given the roots of two binary trees `p` and `q`, write a function to check if they are the same or not.

### Input Format
- Line 1: Level-order nodes of `p`.
- Line 2: Level-order nodes of `q`.

### Output Format
- `true` or `false`.

### Constraints
- $0 \le \text{nodes} \le 100$
""",
            difficulty=ProblemDifficulty.EASY,
            time_limit=1.0,
            memory_limit=256,
            tags=["trees", "bfs-dfs"],
            starter_code={
                "python": """import sys

def solve():
    lines = sys.stdin.read().splitlines()
    p = lines[0].strip() if len(lines) > 0 else ""
    q = lines[1].strip() if len(lines) > 1 else ""
    print("true" if p == q else "false")

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="1 2 3\n1 2 3", expected_output="true", is_sample=True),
            TestCase(input="1 2\n1 null 2", expected_output="false", is_sample=True),
            TestCase(input="1 2 1\n1 1 2", expected_output="false", is_sample=False)
        ])

        # -------------------------------------------------------------
        # 8. 1-D & 2-D DYNAMIC PROGRAMMING
        # -------------------------------------------------------------

        # Climbing Stairs
        seed_problem(db, Problem(
            title="Climbing Stairs",
            slug="climbing-stairs",
            description=r"""You are climbing a staircase. It takes `n` steps to reach the top. Each time you can either climb 1 or 2 steps. In how many distinct ways can you climb to the top?

### Input Format
- Single integer `n`.

### Output Format
- Single integer representing distinct ways.

### Constraints
- $1 \le n \le 45$
""",
            difficulty=ProblemDifficulty.EASY,
            time_limit=1.0,
            memory_limit=256,
            tags=["dynamic-programming", "math"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        return
    n = int(line)
    if n <= 2:
        print(n)
        return
    a, b = 1, 2
    for _ in range(3, n + 1):
        a, b = b, a + b
    print(b)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="2", expected_output="2", is_sample=True),
            TestCase(input="3", expected_output="3", is_sample=True),
            TestCase(input="5", expected_output="8", is_sample=False)
        ])

        # House Robber
        seed_problem(db, Problem(
            title="House Robber",
            slug="house-robber",
            description=r"""You are a professional robber planning to rob houses along a street without alerting the police by robbing two adjacent houses. Return maximum amount possible.

### Input Format
- Space-separated integers representing money in each house.

### Output Format
- Maximum stashed money.

### Constraints
- $1 \le \text{nums.length} \le 100$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["dynamic-programming", "array"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        print("0")
        return
    nums = list(map(int, line.split()))
    rob1, rob2 = 0, 0
    for n in nums:
        temp = max(n + rob1, rob2)
        rob1 = rob2
        rob2 = temp
    print(rob2)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="1 2 3 1", expected_output="4", is_sample=True),
            TestCase(input="2 7 9 3 1", expected_output="12", is_sample=True),
            TestCase(input="2 1 1 2", expected_output="4", is_sample=False)
        ])

        # House Robber II
        seed_problem(db, Problem(
            title="House Robber II",
            slug="house-robber-ii",
            description=r"""All houses at this place are arranged in a circle. That means the first house is the neighbor of the last one. Return the maximum amount of money you can rob tonight without alerting the police.

### Input Format
- Space-separated integers representing `nums`.

### Output Format
- Single integer representing maximum money.

### Constraints
- $1 \le \text{nums.length} \le 100$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["dynamic-programming", "array"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        print("0")
        return
    nums = list(map(int, line.split()))
    if len(nums) == 1:
        print(nums[0])
        return
        
    def rob_linear(houses):
        r1, r2 = 0, 0
        for h in houses:
            temp = max(h + r1, r2)
            r1 = r2
            r2 = temp
        return r2
        
    ans = max(rob_linear(nums[1:]), rob_linear(nums[:-1]))
    print(ans)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="2 3 2", expected_output="3", is_sample=True),
            TestCase(input="1 2 3 1", expected_output="4", is_sample=True),
            TestCase(input="1 2 3", expected_output="3", is_sample=False)
        ])

        # Coin Change
        seed_problem(db, Problem(
            title="Coin Change",
            slug="coin-change",
            description=r"""Given coin denominations `coins` and `amount`, return fewest coins to make up that amount, or `-1`.

### Input Format
- Line 1: Space-separated coin denominations.
- Line 2: Integer `amount`.

### Output Format
- Fewest coins count, or `-1`.

### Constraints
- $1 \le \text{coins.length} \le 12$
- $0 \le \text{amount} \le 10^4$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["dynamic-programming"],
            starter_code={
                "python": """import sys

def solve():
    lines = sys.stdin.read().splitlines()
    if len(lines) < 2:
        return
    coins = list(map(int, lines[0].split()))
    amount = int(lines[1])
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for a in range(1, amount + 1):
        for c in coins:
            if a - c >= 0:
                dp[a] = min(dp[a], 1 + dp[a - c])
    print(dp[amount] if dp[amount] != float('inf') else -1)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="1 2 5\n11", expected_output="3", is_sample=True),
            TestCase(input="2\n3", expected_output="-1", is_sample=True),
            TestCase(input="1\n0", expected_output="0", is_sample=False)
        ])

        # Maximum Subarray
        seed_problem(db, Problem(
            title="Maximum Subarray",
            slug="maximum-subarray",
            description=r"""Given an integer array `nums`, find the subarray with the largest sum, and return its sum.

### Input Format
- Space-separated integers representing `nums`.

### Output Format
- Single integer maximum subarray sum.

### Constraints
- $1 \le \text{nums.length} \le 10^5$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["array", "dynamic-programming"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        return
    nums = list(map(int, line.split()))
    max_sum = nums[0]
    cur_sum = 0
    for n in nums:
        cur_sum = max(n, cur_sum + n)
        max_sum = max(max_sum, cur_sum)
    print(max_sum)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="-2 1 -3 4 -1 2 1 -5 4", expected_output="6", is_sample=True),
            TestCase(input="1", expected_output="1", is_sample=True),
            TestCase(input="5 4 -1 7 8", expected_output="23", is_sample=False)
        ])

        # Maximum Product Subarray
        seed_problem(db, Problem(
            title="Maximum Product Subarray",
            slug="maximum-product-subarray",
            description=r"""Given an integer array `nums`, find a subarray that has the largest product, and return the product.

### Input Format
- Space-separated integers `nums`.

### Output Format
- Single integer representing maximum product.

### Constraints
- $1 \le \text{nums.length} \le 2 \times 10^4$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["array", "dynamic-programming"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        return
    nums = list(map(int, line.split()))
    res = max(nums)
    cur_min, cur_max = 1, 1
    for n in nums:
        if n == 0:
            cur_min, cur_max = 1, 1
            continue
        temp = cur_max * n
        cur_max = max(n * cur_max, n * cur_min, n)
        cur_min = min(temp, n * cur_min, n)
        res = max(res, cur_max)
    print(res)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="2 3 -2 4", expected_output="6", is_sample=True),
            TestCase(input="-2 0 -1", expected_output="0", is_sample=True),
            TestCase(input="-2 3 -4", expected_output="24", is_sample=False)
        ])

        # Longest Increasing Subsequence
        seed_problem(db, Problem(
            title="Longest Increasing Subsequence",
            slug="longest-increasing-subsequence",
            description=r"""Given an integer array `nums`, return the length of the longest strictly increasing subsequence.

### Input Format
- Space-separated integers representing `nums`.

### Output Format
- Single integer length.

### Constraints
- $1 \le \text{nums.length} \le 2500$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["dynamic-programming", "binary-search"],
            starter_code={
                "python": """import sys
import bisect

def solve():
    line = sys.stdin.read().strip()
    if not line:
        print("0")
        return
    nums = list(map(int, line.split()))
    sub = []
    for x in nums:
        idx = bisect.bisect_left(sub, x)
        if idx == len(sub):
            sub.append(x)
        else:
            sub[idx] = x
    print(len(sub))

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="10 9 2 5 3 7 101 18", expected_output="4", is_sample=True),
            TestCase(input="0 1 0 3 2 3", expected_output="4", is_sample=True),
            TestCase(input="7 7 7 7 7 7 7", expected_output="1", is_sample=False)
        ])

        # Longest Common Subsequence
        seed_problem(db, Problem(
            title="Longest Common Subsequence",
            slug="longest-common-subsequence",
            description=r"""Given two strings `text1` and `text2`, return the length of their longest common subsequence.

### Input Format
- Line 1: String `text1`.
- Line 2: String `text2`.

### Output Format
- Single integer length.

### Constraints
- $1 \le \text{text1.length}, \text{text2.length} \le 1000$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["dynamic-programming"],
            starter_code={
                "python": """import sys

def solve():
    lines = sys.stdin.read().splitlines()
    if len(lines) < 2:
        print("0")
        return
    t1, t2 = lines[0].strip(), lines[1].strip()
    m, n = len(t1), len(t2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            if t1[i] == t2[j]:
                dp[i][j] = 1 + dp[i + 1][j + 1]
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])
    print(dp[0][0])

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="abcde\nace", expected_output="3", is_sample=True),
            TestCase(input="abc\nabc", expected_output="3", is_sample=True),
            TestCase(input="abc\ndef", expected_output="0", is_sample=False)
        ])

        # Unique Paths
        seed_problem(db, Problem(
            title="Unique Paths",
            slug="unique-paths",
            description=r"""A robot is on an $m \times n$ grid. The robot is initially located at the top-left corner and tries to reach the bottom-right corner. The robot can only move either down or right at any point in time.

Return the number of possible unique paths.

### Input Format
- Line 1: Integer $m$ (rows).
- Line 2: Integer $n$ (columns).

### Output Format
- Single integer number of unique paths.

### Constraints
- $1 \le m, n \le 100$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["dynamic-programming", "math"],
            starter_code={
                "python": """import sys
import math

def solve():
    lines = sys.stdin.read().splitlines()
    if len(lines) < 2:
        return
    m = int(lines[0].strip())
    n = int(lines[1].strip())
    print(math.comb(m + n - 2, m - 1))

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="3\n7", expected_output="28", is_sample=True),
            TestCase(input="3\n2", expected_output="3", is_sample=True),
            TestCase(input="1\n1", expected_output="1", is_sample=False)
        ])

        # Jump Game
        seed_problem(db, Problem(
            title="Jump Game",
            slug="jump-game",
            description=r"""You are given an integer array `nums`. You are initially positioned at the array's first index, and each element in the array represents your maximum jump length at that position.

Return `true` if you can reach the last index, or `false` otherwise.

### Input Format
- A single line of space-separated integers representing `nums`.

### Output Format
- `true` or `false`.

### Constraints
- $1 \le \text{nums.length} \le 10^4$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["greedy", "dynamic-programming"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        return
    nums = list(map(int, line.split()))
    goal = len(nums) - 1
    for i in range(len(nums) - 1, -1, -1):
        if i + nums[i] >= goal:
            goal = i
    print("true" if goal == 0 else "false")

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="2 3 1 1 4", expected_output="true", is_sample=True),
            TestCase(input="3 2 1 0 4", expected_output="false", is_sample=True),
            TestCase(input="0", expected_output="true", is_sample=False)
        ])

        # -------------------------------------------------------------
        # 9. INTERVALS
        # -------------------------------------------------------------

        # Merge Intervals
        seed_problem(db, Problem(
            title="Merge Intervals",
            slug="merge-intervals",
            description=r"""Given an array of intervals where `intervals[i] = [start_i, end_i]`, merge all overlapping intervals, and return an array of the non-overlapping intervals that cover all the intervals in the input.

### Input Format
- Each line contains two space-separated integers: `start end`.

### Output Format
- Each merged interval `start end` on a separate line (sorted by start).

### Constraints
- $1 \le \text{intervals.length} \le 10^4$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["intervals", "array"],
            starter_code={
                "python": """import sys

def solve():
    lines = sys.stdin.read().splitlines()
    intervals = []
    for line in lines:
        if line.strip():
            intervals.append(list(map(int, line.split())))
    if not intervals:
        return
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for cur in intervals[1:]:
        prev = merged[-1]
        if cur[0] <= prev[1]:
            prev[1] = max(prev[1], cur[1])
        else:
            merged.append(cur)
    for iv in merged:
        print(f"{iv[0]} {iv[1]}")

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="1 3\n2 6\n8 10\n15 18", expected_output="1 6\n8 10\n15 18", is_sample=True),
            TestCase(input="1 4\n4 5", expected_output="1 5", is_sample=True),
            TestCase(input="1 4\n0 4", expected_output="0 4", is_sample=False)
        ])

        # Non-overlapping Intervals
        seed_problem(db, Problem(
            title="Non-overlapping Intervals",
            slug="non-overlapping-intervals",
            description=r"""Given an array of intervals `intervals` where `intervals[i] = [start_i, end_i]`, return the minimum number of intervals you need to remove to make the rest of the intervals non-overlapping.

### Input Format
- Each line contains two space-separated integers representing an interval `start end`.

### Output Format
- Single integer representing minimum removals needed.

### Constraints
- $1 \le \text{intervals.length} \le 10^5$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["intervals", "greedy"],
            starter_code={
                "python": """import sys

def solve():
    lines = sys.stdin.read().splitlines()
    intervals = []
    for line in lines:
        if line.strip():
            intervals.append(list(map(int, line.split())))
    if not intervals:
        print("0")
        return
    intervals.sort(key=lambda x: x[1])
    res = 0
    prev_end = intervals[0][1]
    for start, end in intervals[1:]:
        if start < prev_end:
            res += 1
        else:
            prev_end = end
    print(res)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="1 2\n2 3\n3 4\n1 3", expected_output="1", is_sample=True),
            TestCase(input="1 2\n1 2\n1 2", expected_output="2", is_sample=True),
            TestCase(input="1 2\n2 3", expected_output="0", is_sample=False)
        ])

        # -------------------------------------------------------------
        # 10. MATRIX & 2D GRIDS
        # -------------------------------------------------------------

        # Number of Islands
        seed_problem(db, Problem(
            title="Number of Islands",
            slug="number-of-islands",
            description=r"""Given an $m \times n$ 2D binary grid `grid` which represents a map of `'1'`s (land) and `'0'`s (water), return the number of islands.

An island is surrounded by water and is formed by connecting adjacent lands horizontally or vertically.

### Input Format
- Each line represents a row of the grid with space-separated values (`1` or `0`).

### Output Format
- Single integer count of islands.

### Constraints
- $1 \le m, n \le 300$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.5,
            memory_limit=256,
            tags=["graphs", "bfs-dfs", "matrix"],
            starter_code={
                "python": """import sys

def solve():
    lines = sys.stdin.read().splitlines()
    grid = [line.split() for line in lines if line.strip()]
    if not grid:
        print("0")
        return
    rows, cols = len(grid), len(grid[0])
    islands = 0
    
    def dfs(r, c):
        if r < 0 or c < 0 or r >= rows or c >= cols or grid[r][c] != '1':
            return
        grid[r][c] = '0'
        dfs(r + 1, c)
        dfs(r - 1, c)
        dfs(r, c + 1)
        dfs(r, c - 1)
        
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '1':
                dfs(r, c)
                islands += 1
    print(islands)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="1 1 1 1 0\n1 1 0 1 0\n1 1 0 0 0\n0 0 0 0 0", expected_output="1", is_sample=True),
            TestCase(input="1 1 0 0 0\n1 1 0 0 0\n0 0 1 0 0\n0 0 0 1 1", expected_output="3", is_sample=True),
            TestCase(input="0 0 0\n0 0 0", expected_output="0", is_sample=False)
        ])

        # Set Matrix Zeroes
        seed_problem(db, Problem(
            title="Set Matrix Zeroes",
            slug="set-matrix-zeroes",
            description=r"""Given an $m \times n$ integer matrix `matrix`, if an element is 0, set its entire row and column to 0's.

### Input Format
- Each line represents a matrix row of space-separated integers.

### Output Format
- Modified matrix row by row.

### Constraints
- $1 \le m, n \le 200$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["matrix", "array"],
            starter_code={
                "python": """import sys

def solve():
    lines = sys.stdin.read().splitlines()
    matrix = [list(map(int, line.split())) for line in lines if line.strip()]
    if not matrix:
        return
    rows, cols = len(matrix), len(matrix[0])
    zero_rows = set()
    zero_cols = set()
    for r in range(rows):
        for c in range(cols):
            if matrix[r][c] == 0:
                zero_rows.add(r)
                zero_cols.add(c)
    for r in range(rows):
        for c in range(cols):
            if r in zero_rows or c in zero_cols:
                matrix[r][c] = 0
    for row in matrix:
        print(" ".join(map(str, row)))

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="1 1 1\n1 0 1\n1 1 1", expected_output="1 0 1\n0 0 0\n1 0 1", is_sample=True),
            TestCase(input="0 1 2 0\n3 4 5 2\n1 3 1 5", expected_output="0 0 0 0\n0 4 5 0\n0 3 1 0", is_sample=True),
            TestCase(input="1 2 3", expected_output="1 2 3", is_sample=False)
        ])

        # Rotate Image
        seed_problem(db, Problem(
            title="Rotate Image",
            slug="rotate-image",
            description=r"""You are given an $n \times n$ 2D matrix representing an image, rotate the image by 90 degrees (clockwise) in-place.

### Input Format
- Each line represents an $n \times n$ matrix row.

### Output Format
- 90-degree rotated matrix rows.

### Constraints
- $1 \le n \le 20$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["matrix", "array"],
            starter_code={
                "python": """import sys

def solve():
    lines = sys.stdin.read().splitlines()
    matrix = [list(map(int, line.split())) for line in lines if line.strip()]
    if not matrix:
        return
    matrix.reverse()
    for i in range(len(matrix)):
        for j in range(i):
            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]
    for row in matrix:
        print(" ".join(map(str, row)))

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="1 2 3\n4 5 6\n7 8 9", expected_output="7 4 1\n8 5 2\n9 6 3", is_sample=True),
            TestCase(input="5 1 9 11\n2 4 8 10\n13 3 6 7\n15 14 12 16", expected_output="15 13 2 5\n14 3 4 1\n12 6 8 9\n16 7 10 11", is_sample=True)
        ])

        # -------------------------------------------------------------
        # 11. BIT MANIPULATION
        # -------------------------------------------------------------

        # Number of 1 Bits
        seed_problem(db, Problem(
            title="Number of 1 Bits",
            slug="number-of-1-bits",
            description=r"""Write a function that takes the binary representation of a positive integer and returns the number of set bits it has (also known as the Hamming weight).

### Input Format
- A single integer `n`.

### Output Format
- Single integer count of 1 bits.

### Constraints
- $1 \le n \le 2^{31} - 1$
""",
            difficulty=ProblemDifficulty.EASY,
            time_limit=1.0,
            memory_limit=256,
            tags=["bit-manipulation"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        return
    n = int(line)
    print(bin(n).count('1'))

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="11", expected_output="3", is_sample=True),
            TestCase(input="128", expected_output="1", is_sample=True),
            TestCase(input="2147483645", expected_output="30", is_sample=False)
        ])

        # Counting Bits
        seed_problem(db, Problem(
            title="Counting Bits",
            slug="counting-bits",
            description=r"""Given an integer `n`, return an array `ans` of length `n + 1` such that for each $i$ ($0 \le i \le n$), `ans[i]` is the number of `1`'s in the binary representation of $i$.

### Input Format
- Single integer `n`.

### Output Format
- Space-separated integers representing `ans`.

### Constraints
- $0 \le n \le 10^5$
""",
            difficulty=ProblemDifficulty.EASY,
            time_limit=1.0,
            memory_limit=256,
            tags=["bit-manipulation", "dynamic-programming"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        return
    n = int(line)
    dp = [0] * (n + 1)
    for i in range(1, n + 1):
        dp[i] = dp[i >> 1] + (i & 1)
    print(" ".join(map(str, dp)))

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="2", expected_output="0 1 1", is_sample=True),
            TestCase(input="5", expected_output="0 1 1 2 1 2", is_sample=True),
            TestCase(input="8", expected_output="0 1 1 2 1 2 2 3 1", is_sample=False)
        ])

        # Missing Number
        seed_problem(db, Problem(
            title="Missing Number",
            slug="missing-number",
            description=r"""Given an array `nums` containing `n` distinct numbers in the range `[0, n]`, return the only number in the range that is missing from the array.

### Input Format
- Space-separated integers `nums`.

### Output Format
- Single integer missing number.

### Constraints
- $n == \text{nums.length}$
- $1 \le n \le 10^4$
""",
            difficulty=ProblemDifficulty.EASY,
            time_limit=1.0,
            memory_limit=256,
            tags=["bit-manipulation", "array", "math"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        return
    nums = list(map(int, line.split()))
    n = len(nums)
    expected = n * (n + 1) // 2
    print(expected - sum(nums))

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="3 0 1", expected_output="2", is_sample=True),
            TestCase(input="0 1", expected_output="2", is_sample=True),
            TestCase(input="9 6 4 2 3 5 7 0 1", expected_output="8", is_sample=False)
        ])

        # Reverse Bits
        seed_problem(db, Problem(
            title="Reverse Bits",
            slug="reverse-bits",
            description=r"""Reverse bits of a given 32-bit unsigned integer.

### Input Format
- A single 32-bit unsigned integer `n`.

### Output Format
- A single integer representing the number with reversed binary bits.

### Constraints
- The input must be a 32-bit unsigned integer.
""",
            difficulty=ProblemDifficulty.EASY,
            time_limit=1.0,
            memory_limit=256,
            tags=["bit-manipulation"],
            starter_code={
                "python": """import sys

def solve():
    line = sys.stdin.read().strip()
    if not line:
        return
    n = int(line)
    res = 0
    for _ in range(32):
        res = (res << 1) | (n & 1)
        n >>= 1
    print(res)

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="43261596", expected_output="964176192", is_sample=True),
            TestCase(input="1", expected_output="2147483648", is_sample=True),
            TestCase(input="0", expected_output="0", is_sample=False)
        ])

        # Sum of Two Integers
        seed_problem(db, Problem(
            title="Sum of Two Integers",
            slug="sum-of-two-integers",
            description=r"""Given two integers `a` and `b`, return the sum of the two integers without using the operators `+` and `-`.

### Input Format
- Line 1: Integer `a`.
- Line 2: Integer `b`.

### Output Format
- Single integer representing $a + b$.

### Constraints
- $-1000 \le a, b \le 1000$
""",
            difficulty=ProblemDifficulty.MEDIUM,
            time_limit=1.0,
            memory_limit=256,
            tags=["bit-manipulation"],
            starter_code={
                "python": """import sys

def solve():
    lines = sys.stdin.read().splitlines()
    if len(lines) < 2:
        return
    a = int(lines[0].strip())
    b = int(lines[1].strip())
    
    # 32 bit mask in Python
    mask = 0xffffffff
    while (b & mask) > 0:
        carry = (a & b) << 1
        a = (a ^ b)
        b = carry
    print(a if b > 0 else (a & mask) if a < 0x80000000 else ~(a ^ mask))

if __name__ == '__main__':
    solve()
"""
            }
        ), [
            TestCase(input="1\n2", expected_output="3", is_sample=True),
            TestCase(input="2\n3", expected_output="5", is_sample=True),
            TestCase(input="-1\n1", expected_output="0", is_sample=False)
        ])

        print("[*] Initializing RAG Knowledge Base vectors (pgvector)...")
        rag_service.seed_problem_knowledge_if_needed(db)

        print("[OK] Complete Blind 75 database sync finished successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == '__main__':
    seed_data()
