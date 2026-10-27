document.addEventListener('DOMContentLoaded',()=>{document.querySelectorAll('.alert').forEach(a=>setTimeout(()=>a.remove(),5000));document.querySelectorAll('[data-confirm]').forEach(b=>b.addEventListener('click',e=>{if(!confirm(b.dataset.confirm))e.preventDefault()}));const group=document.querySelector('#blood_group');const compatible=document.querySelector('#compatible-groups');if(group&&compatible){const map=JSON.parse(compatible.dataset.map);const update=()=>{compatible.textContent=(map[group.value]||[]).join(', ')||'Select a patient blood group';};group.addEventListener('change',update);update();}document.querySelectorAll('[data-filter-table]').forEach(input=>input.addEventListener('input',()=>{const table=document.querySelector(input.dataset.filterTable);const term=input.value.toLowerCase();table.querySelectorAll('tbody tr').forEach(row=>row.style.display=row.textContent.toLowerCase().includes(term)?'':'none')}));});

document.addEventListener('DOMContentLoaded',()=>{
  const birthDate=document.querySelector('#dob');
  const lastDonation=document.querySelector('#last_donation');
  const sleepHours=document.querySelector('#sleep_hours');
  const status=document.querySelector('#eligibility-status');
  if(!birthDate||!lastDonation||!sleepHours||!status)return;

  const updateEligibility=()=>{
    const birth=birthDate.value;
    const sleep=Number(sleepHours.value);
    if(!/^\d{4}-\d{2}-\d{2}$/.test(birth)||sleepHours.value===''||!Number.isFinite(sleep)){
      status.textContent='Complete date of birth and sleep hours to check.';
      return;
    }

    const today=new Date();
    const todayString=[today.getFullYear(),String(today.getMonth()+1).padStart(2,'0'),String(today.getDate()).padStart(2,'0')].join('-');
    const birthParts=birth.split('-').map(Number);
    const birthDateValue=new Date(birthParts[0],birthParts[1]-1,birthParts[2]);
    let age=today.getFullYear()-birthDateValue.getFullYear();
    if(today.getMonth()<birthDateValue.getMonth()||(today.getMonth()===birthDateValue.getMonth()&&today.getDate()<birthDateValue.getDate()))age--;

    let eligible=age>=18&&sleep>=6&&sleep<=24&&birth<=todayString;
    if(lastDonation.value){
      const previous=lastDonation.value.split('-').map(Number);
      const monthIndex=previous[1]-1+6;
      const eligibleYear=previous[0]+Math.floor(monthIndex/12);
      const eligibleMonth=monthIndex%12;
      const eligibleDay=Math.min(previous[2],new Date(eligibleYear,eligibleMonth+1,0).getDate());
      const eligibleDate=[eligibleYear,String(eligibleMonth+1).padStart(2,'0'),String(eligibleDay).padStart(2,'0')].join('-');
      eligible=eligible&&lastDonation.value<=todayString&&todayString>=eligibleDate;
    }
    status.textContent=eligible?'Eligible':'Not eligible';
  };

  [birthDate,lastDonation,sleepHours].forEach(input=>input.addEventListener('input',updateEligibility));
  updateEligibility();
});
