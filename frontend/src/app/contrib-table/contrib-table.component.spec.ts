import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContribTableComponent } from './contrib-table.component';

describe('ContribTableComponent', () => {
  let component: ContribTableComponent;
  let fixture: ComponentFixture<ContribTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ContribTableComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ContribTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
