from locust import HttpUser, between, task


class AdaptivePlannerUser(HttpUser):
    wait_time = between(1, 2)

    @task(8)
    def open_home_page(self):
        self.client.get("/")

    @task(2)
    def invalid_login_expected(self):
        with self.client.post(
            "/auth/login",
            json={
                "email": "wrong@example.com",
                "password": "wrong",
            },
            catch_response=True,
            name="/auth/login invalid expected",
        ) as response:
            if response.status_code in [400, 401]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(1)
    def invalid_register_expected(self):
        with self.client.post(
            "/auth/register",
            json={
                "email": "",
                "password": "",
            },
            catch_response=True,
            name="/auth/register invalid expected",
        ) as response:
            if response.status_code in [400, 401]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
