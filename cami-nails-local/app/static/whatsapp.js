"use strict";
const destination = document.getElementById("whatsapp-destination");
if (destination) {
  const url = new URL(destination.href);
  if (url.origin === "https://wa.me") window.location.replace(url.href);
}
