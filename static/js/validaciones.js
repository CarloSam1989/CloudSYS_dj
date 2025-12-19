/**
 * Valida Cédula Ecuatoriana (10 dígitos)
 * Retorna: { valido: boolean, mensaje: string }
 */
function validarIdentificacionEcuador(identificacion) {
    // 1. Limpiar espacios
    let id = identificacion.trim();

    // 2. Si es Pasaporte (Menos de 10 o más de 10 caracteres, o tiene letras)
    // Asumimos que si tiene letras o longitud distinta a 10 (y no es RUC de 13), es pasaporte.
    if (id.length !== 10 || isNaN(id)) {
        if (id.length < 5) {
            return { valido: false, mensaje: "El documento es muy corto." };
        }
        // Si es alfanumérico o tiene otra longitud, lo damos por válido como PASAPORTE
        return { valido: true, type: 'pasaporte', mensaje: "Formato Pasaporte aceptado." };
    }

    // 3. Validación estricta de CÉDULA (10 dígitos numéricos)
    if (id.length === 10) {
        // Validar provincia (2 primeros dígitos entre 01 y 24, o 30)
        const provincia = parseInt(id.substring(0, 2));
        if (!((provincia >= 1 && provincia <= 24) || provincia === 30)) {
            return { valido: false, mensaje: "Código de provincia inválido." };
        }

        // Validar tercer dígito (debe ser menor a 6 para personas naturales)
        const tercerDigito = parseInt(id.substring(2, 3));
        if (tercerDigito >= 6) {
             // Podría ser RUC de sociedad pública/privada escrito como cédula, pero para CI debe ser < 6
             // Nota: Hay casos raros, pero esta es la regla general.
             return { valido: false, mensaje: "Tercer dígito inválido para Cédula." };
        }

        // Algoritmo Módulo 10
        let total = 0;
        const coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]; // Para los primeros 9 dígitos
        
        for (let i = 0; i < 9; i++) {
            let valor = parseInt(id.charAt(i)) * coeficientes[i];
            total += (valor >= 10) ? (valor - 9) : valor;
        }

        const digitoVerificador = parseInt(id.charAt(9));
        const decenaSuperior = Math.ceil(total / 10) * 10;
        let resultado = decenaSuperior - total;
        
        if (resultado === 10) resultado = 0;

        if (resultado === digitoVerificador) {
            return { valido: true, type: 'cedula', mensaje: "Cédula Válida" };
        } else {
            return { valido: false, mensaje: "Cédula Incorrecta (Dígito verificador falla)." };
        }
    }
    
    return { valido: false, mensaje: "Longitud incorrecta." };
}