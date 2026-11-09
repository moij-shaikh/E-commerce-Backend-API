function show_hide_settings_panel() {
  const token= sessionStorage.getItem("access_token")
  if(!token){
    window.location.href = "/login"
    return
  }
  let panel = document.querySelector(".Settings_panel");
  if (panel.style.display == "block") {
    panel.style.display = "none";
  } else {
    panel.style.display = "block";
  }
}

let change_address = document.querySelector(".change_address_btn");
change_address.addEventListener("click", (e) => {
  let choice = confirm("Do you want to address");
  if (choice) {
    alert("process has started");
  }
});

let logout = document.querySelector(".logout_user_btn");
logout.addEventListener("click",async (e) => {
  let choice = confirm("Do you want to Logout?");
  if (choice) {
    const access_token = sessionStorage.getItem("access_token")
    if (!access_token){
       alert("Login first. ")
    }
    const req = await fetch("/user/auth/logout",{
      method:"Post",
      headers:{
        "Authorization":"Bearer"+access_token
      }
    })
    const res= await req.json()
    if(req.ok){
      sessionStorage.removeItem("access_token")
      alert(res.message)
    }
    else{
      alert(res.detail)
    }

    
  }
});

let delete_user = document.querySelector(".delete_user_btn");
delete_user.addEventListener("click", async (e) => {
  let choice = confirm("Do you really want to Delete the account");
  if (!choice) {
    return
  }
  const token = sessionStorage.getItem("access_token")
  if(!token){
    console.log("not login")
  }
  const req = await fetch("/user/account",{
    method:"POST",
    headers:{
      "Authorization":"Bearer"+token
    }
  })
  const result = await response.json();
    if (response.ok) {
        sessionStorage.removeItem("access_token");
        alert(result.message);
        window.location.href = "/";
    }
    else {
        alert(result.detail);
    }
});

const cart_form=document.querySelectorAll(".add_to_cart_form")
cart_form.forEach(function(from){
  from.addEventListener("submit", async function(e){
    e.preventDefault()
    const token= sessionStorage.getItem("access_token")
    if(!token){
      alert("Please login first. ")
      return
    }
     const form_data = new FormData(form);
     const response = await fetch("/cart",{
      method:"POST",
      headers:{
        "Authorization":"Bearer"+token
      },
      body:form_data
     });
     const result = await response.json();

     if (response.ok) {
         alert("Product added to cart!");
     }
     else {
         alert(result.detail);
     }
  })
})

function move_to_cart_page(){
  const token= sessionStorage.getItem("access_token")
  if(!token){
    window.location.href="/login"
  }
    window.location.href="/cart"

}