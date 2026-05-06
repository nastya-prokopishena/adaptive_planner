import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:5000",
  withCredentials: true
});

export const fetchEvents = async () => {
  const response = await api.get("/api/events");
  return response.data;
};
