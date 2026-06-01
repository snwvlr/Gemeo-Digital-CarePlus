/* CarePlus - lógica da página confirmacao */
function carregarAgendamento() {
            const urlParams = new URLSearchParams(window.location.search);
            
            // Pega a DATA e a HORA da URL
            const dataBruta = urlParams.get('data');
            const horaBruta = urlParams.get('hora'); 
            
            const display = document.getElementById('data-exibicao');

            if (dataBruta) {
                const partes = dataBruta.split('-');
                if (partes.length === 3) {
                    const dataFormatada = `${partes[2]}/${partes[1]}/${partes[0]}`;
                    
                    // Se a hora existir na URL, usa ela. Se não, usa 09:00.
                    const horaFinal = horaBruta ? horaBruta : "09:00";
                    
                    display.innerText = `${dataFormatada} às ${horaFinal}`;
                } else {
                    display.innerText = "Data inválida";
                }
            } else {
                display.innerText = "Data a confirmar";
            }
        }

        window.addEventListener('load', carregarAgendamento);
