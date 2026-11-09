const login_form = document.getElementById("login_form");

login_form.addEventListener("submit", async function(event) {
    event.preventDefault();
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const form_data = new URLSearchParams();
    form_data.append("username", username);
    form_data.append("password", password);
    try {
        const response = await fetch("/user/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            body: form_data,
            credentials: "same-origin"
        });
        const data = await response.json();
        if (!response.ok) {
            document.getElementById("login_message").textContent =
                data.detail;
            return;
        }
        sessionStorage.setItem("access_token", data.access_token);
    }
    catch(error) {
        console.log(error);
        document.getElementById("login_message").textContent =
            "Something went wrong";
    }
});
