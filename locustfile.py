from locust import HttpUser, between, task


class PlannerUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def open_home_page(self):
        self.client.get("/")

    @task
    def unauthorized_events_request(self):
        self.client.get("/api/events")

    @task
    def invalid_login(self):
        self.client.post(
            "/auth/login",
            json={"email": "wrong@example.com", "password": "wrong"},
        )
