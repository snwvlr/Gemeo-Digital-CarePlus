/* CarePlus - lógica da página dispositivo */
// Função para recalibrações locais nos cards
        function recalibrarLocal(tipo) {
            const loader = document.getElementById(`loader-${tipo}`);
            const status = document.getElementById(`status-${tipo}`);
            
            loader.style.display = 'flex';
            if(tipo === 'pressao') status.innerText = "CALIBRANDO";

            setTimeout(() => {
                loader.style.display = 'none';
                if(tipo === 'pressao') {
                    status.innerText = "RECALIBRADO";
                    status.classList.replace('text-primary', 'text-emerald-500');
                } else {
                    status.innerText = "SINCRO.";
                    status.classList.replace('text-amber-500', 'text-emerald-500');
                }
            }, 3000);
        }

        // Função de Sincronização Geral
        function iniciarSincronizacao() {
            const overlay = document.getElementById('sync-overlay');
            const bar = document.getElementById('sync-bar');
            const title = document.getElementById('sync-title');
            const msg = document.getElementById('sync-msg');

            overlay.style.display = 'flex';
            let progresso = 0;

            const intervalo = setInterval(() => {
                progresso += Math.random() * 30;
                if (progresso > 100) progresso = 100;
                bar.style.width = progresso + '%';

                if (progresso === 100) {
                    clearInterval(intervalo);
                    title.innerText = "Sincronizado!";
                    title.classList.add('text-emerald-500');
                    msg.innerText = "Configurações aplicadas com sucesso.";
                    
                    setTimeout(() => {
                        window.location.href = 'index.html';
                    }, 1500);
                }
            }, 600);
        }
