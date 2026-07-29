from locust import HttpUser, task, between
import random
import string


def random_email():
    return f"test_{''.join(random.choices(string.ascii_lowercase, k=8))}@example.com"


class BNSAIUser(HttpUser):
    wait_time = between(1, 3)
    token = None

    def on_start(self):
        email = random_email()
        password = "TestPass123!"
        username = f"user_{''.join(random.choices(string.ascii_lowercase, k=8))}"
        self.client.post("/api/v1/auth/register", json={
            "email": email,
            "username": username,
            "password": password,
            "full_name": "Load Test User"
        })
        response = self.client.post("/api/v1/auth/login", json={
            "username": username,
            "password": password
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")

    @task(5)
    def health_check(self):
        self.client.get("/api/v1/health")

    @task(3)
    def health_detailed(self):
        self.client.get("/api/v1/health/detailed")

    @task(2)
    def list_chats(self):
        if self.token:
            self.client.get("/api/v1/chat/", headers={"Authorization": f"Bearer {self.token}"})

    @task(2)
    def list_drafts(self):
        if self.token:
            self.client.get("/api/v1/drafting/documents", headers={"Authorization": f"Bearer {self.token}"})

    @task(1)
    def get_me(self):
        if self.token:
            self.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {self.token}"})

    @task(1)
    def draft_types(self):
        if self.token:
            self.client.get("/api/v1/drafting/types", headers={"Authorization": f"Bearer {self.token}"})


class AuthEndpointsUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def register_login(self):
        email = random_email()
        password = "TestPass123!"
        username = f"user_{''.join(random.choices(string.ascii_lowercase, k=8))}"
        self.client.post("/api/v1/auth/register", json={
            "email": email,
            "username": username,
            "password": password,
            "full_name": "Load Test User"
        })
        self.client.post("/api/v1/auth/login", json={
            "username": username,
            "password": password
        })

    @task(1)
    def health_check(self):
        self.client.get("/api/v1/health")
