// xades_factura_electronica_sri.js

async function firmarFactura(xmlOriginal, nombreArchivo) {
    try {
      const certificado = await seleccionarCertificado();
      const firmado = await firmarXMLConCertificado(xmlOriginal, certificado);
      saveFile_noui(firmado, nombreArchivo || "factura_firmada.xml");
      alert("✅ XML firmado correctamente.");
    } catch (e) {
      console.error("❌ Error al firmar el XML:", e);
      alert("❌ No se pudo firmar el XML.");
    }
  }
  
  async function seleccionarCertificado() {
    const certificados = await window.crypto.subtle.listCertificates?.() || [];
    if (!certificados.length) throw new Error("No se encontraron certificados.");
    return certificados[0]; // Usar el primero por simplicidad
  }
  
  async function firmarXMLConCertificado(xml, cert) {
    // En un entorno real deberías usar WebCrypto + WebAssembly (ej. xml-crypto) o una lib local
    // Aquí simulamos la firma para propósitos de demostración
    return xml.replace("<factura", "<factura><Signature>Simulada</Signature>");
  }
  
  // Esta función guarda el archivo localmente
  function saveFile_noui(content, filename) {
    const blob = new Blob([content], { type: "text/xml" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }
  